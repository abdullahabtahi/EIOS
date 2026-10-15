"""FastAPI Cockpit API Gateway.

Wraps the Cockpit Presentation Engine and underlying services:
- CockpitShellPresenter
- ExecutiveCockpitService
- AMLWorkstationService
- PartnerWorkstationService
- ComplianceExplorerService
- DataPlatformOperationsService
- GovernedActionShelf
- DecisionOutcomesLedger

Serves full contract-compliant JSON payloads adhering to
specs/016-cockpit-frontend/contracts/cockpit-ui-contract.schema.json.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any, cast

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from eios.assistant.config import AssistantConfigError
from eios.assistant.sessions import valid_entity_id
from eios.assistant.telemetry import record_turn
from eios.cockpit import aml_engine_view as aml_view
from eios.cockpit import compliance_view, operations_view
from eios.cockpit import geo as geo_routes
from eios.cockpit import executive_view as exec_view
from eios.cockpit import partner_engine_view as partner_view
from eios.cockpit.aml_engine_view import default_entity
from eios.cockpit.assistant_gateway import (
    get_runtime,
)
from eios.cockpit.assistant_gateway import response_body as assistant_response_body
from eios.cockpit.auth import (
    APPROVE_ROLES,
    STAGE_ROLES,
    Operator,
    cors_origins,
    current_operator,
    require_roles,
)
from eios.cockpit.executive_view import format_metric
from eios.cockpit.governance_shelf import GovernedActionCard
from eios.cockpit.ratelimit import limit_copilot
from eios.cockpit.session import SessionManager
from eios.cockpit.shell import CockpitShellPresenter
from eios.dataplane.aml_service import EngineAMLService, UnknownAccountError
from eios.dataplane.ops_service import EngineOperationsService
from eios.dataplane.partner_service import EnginePartnerService
from eios.dataplane.plane import (
    engine_service,
    executive_engine_service,
    operations_engine_service,
    partner_engine_service,
    read_models,
)
from eios.dataplane.plane import governance as plane_governance
from eios.flywheel.ledger import DecisionOutcomeRecord
from eios.llm_gateway.providers.registry import UnknownModelError
from eios.ontology.actions.audit import ContinuousAuditWalker
from eios.ontology.actions.intent_hub import (
    CANONICAL_ACTION_SPECS,
    ConcurrentModificationError,
    FourEyesViolationError,
    InvalidActionParameterError,
)
from eios.ontology.actions.models import (
    ActionIntentToken,
)
from eios.ontology.omcp.port.contracts import PortError
from eios.ontology.omcp.port.principal import principal_for

_LOG = logging.getLogger("eios.cockpit.server")


API_VERSION = "0.19.0"

app = FastAPI(
    title="EIOS Cockpit Presentation Gateway",
    version=API_VERSION,
    description="Institutional Operator Cockpit API Gateway powering EIOS high-density operational cockpit",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Global Service Singletons
session_mgr = SessionManager()
governance = plane_governance()
# Seed demo intents once on startup for local / dev / test environments
if os.getenv("EIOS_ENVIRONMENT", "dev") in {"dev", "test"}:
    governance.seed_demo_intents()

action_shelf = governance.shelf
presenter = CockpitShellPresenter(session_manager=session_mgr, action_shelf=action_shelf)
# One set of read models under every route and the assistant (spec 031 FR-008): a screen and an answer read the
# same objects. `EIOS_DATA_PLANE` chooses engine-backed or fixture AML data.
_models = read_models()
executive_svc = _models.executive
aml_svc = _models.aml
partner_svc = _models.partner
compliance_svc = _models.compliance
operations_svc = _models.operations
outcomes_ledger = _models.outcomes


# Request/Response Models
class SimulateRequest(BaseModel):
    shock_param: str = "competitor_payout_increase"
    magnitude_pct: float = 25.0


class WhatIfSimulationResponse(BaseModel):
    shock_param: str = Field(..., description="Causal shock parameter identifier")
    magnitude_pct: float = Field(..., description="Shock magnitude percentage")
    latency_ms: float = Field(..., description="Simulation latency in milliseconds")
    projected_changes: dict[str, float] = Field(..., description="Projected KPI impact deltas")
    mitigations: list[dict[str, Any]] = Field(default_factory=list, description="Ranked defences")
    mitigation_basis: str | None = None
    extrapolates_beyond_history: bool = False
    causal_label: str | None = None
    causal_reason: str | None = None
    attribution_waterfall: list[dict[str, Any]] = Field(..., description="Attribution breakdown")
    attribution_sum_pct: float = Field(..., description="Attribution sum percentage")
    confidence_interval: list[float] = Field(..., description="Lower and upper bounds")


class StageActionRequest(BaseModel):
    action_type: str = Field(..., description="Canonical action type name")
    target_entity_id: str = Field(..., description="Target business entity ID")
    severity: str = Field(default="HIGH", description="Severity classification")
    initiator_officer_id: str | None = Field(
        default=None, description="Optional officer identifier for dev/test staging"
    )
    requires_four_eyes: bool = Field(
        default=True, description="Whether action requires dual approval"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Action parameters and context"
    )


class StageActionResponse(BaseModel):
    status: str = Field(default="STAGED", description="Action lifecycle status")
    card: dict[str, Any] = Field(
        ..., description="Governed action card contract conforming to UI spec"
    )
    total_staged: int = Field(..., description="Total active staged actions count")


class AuthorizeActionRequest(BaseModel):
    intent_id: str = Field(..., description="Target action intent ID")
    authorizer_id: str = Field(..., description="Authorizing officer ID")
    second_eye_token: str | None = Field(
        default=None, description="Optional second-eye verification token"
    )


class AuthorizeActionResponse(BaseModel):
    status: str = Field(
        ...,
        description="Action lifecycle transition outcome (PENDING_SECOND_EYE, COMMITTED, APPROVED)",
    )
    card: dict[str, Any] = Field(..., description="Updated governed action card contract")
    committed_timestamp: str = Field(
        ..., description="Approval/commit timestamp in ISO 8601 UTC format"
    )


MAX_QUERY_CHARS = 2000  # [ASSUMPTION] a long prompt is a cheap way to spend model budget; no real question needs more


class CopilotQueryRequest(BaseModel):
    """`activeEntityId` is the name the browser sends today; both names are accepted until the browser is aligned."""

    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    context_entity_id: str | None = Field(
        default=None, validation_alias=AliasChoices("context_entity_id", "activeEntityId")
    )
    role: str = "executive"
    model: str | None = (
        None  # a registry key from GET /api/cockpit/copilot/models; None runs the default
    )


class FlywheelFeedbackRequest(BaseModel):
    case_id: str = Field(..., description="Investigation case reference")
    feedback_type: str = Field(
        default="SAR_NARRATIVE_EDIT", description="Annotation or revision type"
    )
    original_text: str = Field(..., description="Original model-generated text")
    revised_text: str = Field(..., description="Operator-revised ground truth text")
    annotator_id: str | None = Field(default=None, description="Annotator identifier")
    false_positive: bool = Field(default=False, description="Whether alert was a false positive")
    propensity_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Propensity score at decision time"
    )


class FlywheelFeedbackResponse(BaseModel):
    status: str = Field(default="RECORDED", description="Feedback recording status")
    decision_id: str = Field(..., description="Decision identifier in outcomes ledger")
    provenance_hash: str = Field(..., description="Cryptographic SHA-256 provenance hash")
    total_flywheel_records: int = Field(..., description="Total feedback records count in ledger")
    timestamp: str = Field(..., description="Feedback receipt timestamp")


class AuditVerifyResponse(BaseModel):
    status: str = Field(..., description="Continuity verification outcome: VALID or TAMPERED")
    total_records: int = Field(..., description="Total records walked in hash chain")
    last_hash: str = Field(..., description="Head SHA-256 block hash")
    genesis_hash: str = Field(..., description="Genesis SHA-256 block hash")
    tampered_sequence_id: int | None = Field(
        default=None, description="Sequence ID of corrupted block if tampered"
    )
    failure_reason: str | None = Field(
        default=None, description="Detailed failure diagnosis if invalid"
    )
    worm_checkpoints_verified: int = Field(
        ..., description="Count of validated WORM signed checkpoints"
    )
    worm_mode: str = Field(..., description="WORM mode: SIGNED_CHECKPOINTS or NO_CHECKPOINTS")
    audit_duration_ms: float = Field(
        ..., description="Wall-clock audit traversal latency in milliseconds"
    )
    verified_at: str = Field(..., description="Audit run timestamp")


class CockpitHealthResponse(BaseModel):
    status: str = Field(default="UP", description="Gateway health status")
    version: str = Field(..., description="API runtime version")
    service: str = Field(..., description="Service identifier")
    engine: str = Field(..., description="Underlying presentation engine")
    design_system: str = Field(..., description="Design system token standard")
    security_standard: str = Field(..., description="Cryptographic security standard")
    sse_enabled: bool = Field(default=True, description="Whether Server-Sent Events are enabled")
    cors_configured: bool = Field(default=True, description="Whether CORS is explicitly secured")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")


# Workstation payloads are assembled from in-process fixtures, not from the ingestion pipeline, so the
# contract says so. "[LIVE]" must wait until a state actually arrives from governed data products.
FIXTURE_DATA_BADGE = "[ILLUSTRATIVE]"
ENGINE_DATA_BADGE = "[ENGINE]"  # computed by the engines over the seeded world, not hand-written
AML_ROLES = ("aml_investigator", "aml", "compliance_aml")
PARTNER_ROLES = ("partner_manager", "partner", "growth")
LIVE_DATA_BADGE = "[LIVE]"  # read from the running governance ledger


def _data_badge(role_enum: str) -> str:
    """Where this workstation's numbers come from: engines over the seeded worlds, the live ledger, or fixtures."""
    if role_enum == "aml_investigator" and engine_service() is not None:
        return ENGINE_DATA_BADGE
    if role_enum == "partner_manager" and partner_engine_service() is not None:
        return ENGINE_DATA_BADGE
    if role_enum == "executive" and executive_engine_service() is not None:
        return ENGINE_DATA_BADGE
    if role_enum == "data_operations" and operations_engine_service() is not None:
        return ENGINE_DATA_BADGE
    if role_enum == "compliance_auditor" and compliance_svc.sequencer is not None:
        return LIVE_DATA_BADGE
    return FIXTURE_DATA_BADGE


def _get_utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _card_to_ui_contract_dict(
    card: GovernedActionCard, token: ActionIntentToken | None = None
) -> dict[str, Any]:
    lifecycle_state = "STAGED"
    if card.status == "PENDING_APPROVAL":
        if card.first_approver_id:
            lifecycle_state = "PENDING_SECOND_EYE"
        else:
            lifecycle_state = "STAGED"
    elif card.status in ("APPROVED", "EXECUTED"):
        lifecycle_state = "COMMITTED"
    elif card.status in ("ABORTED", "REJECTED"):
        lifecycle_state = "REJECTED"
    elif card.status == "EXPIRED":
        lifecycle_state = "EXPIRED"

    kms_key_id = token.kms_key_id if token else ""
    sig_digest = token.signature if token else ""

    sev = card.severity.upper() if card.severity else "HIGH"
    if sev not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        sev = "HIGH"

    initiator = card.first_approver_id or (token.requester_agent_id if token else "SYSTEM")

    return {
        "intent_id": card.intent_id,
        "action_type": card.action_type,
        "target_entity_id": card.target_entity_id,
        "severity": sev,
        "lifecycle_state": lifecycle_state,
        "kms_signature": {
            "key_id": kms_key_id,
            "algorithm": "ECDSA_P256_SHA256",
            "signature_digest": sig_digest,
            "verified": card.kms_signature_verified,
        },
        "requires_four_eyes": card.requires_four_eyes,
        "initiator_officer_id": initiator,
        "second_officer_id": card.second_approver_id,
    }


def _ensure_default_staged_cards() -> None:
    """Explicit hook to seed demo intents once across all instances (create-if-absent)."""
    governance.seed_demo_intents()


def _flywheel_status() -> dict[str, Any]:
    """Feedback and calibration state. On the engine plane the drift flag is measured; what has no count says so."""
    models = read_models()
    sample = models.calibration_sample
    if sample is None:
        return {
            "total_feedback_events": outcomes_ledger.count(),
            "uncalibrated_discrepancies": 2,
            "calibration_drift_detected": False,
        }
    report = models.calibration.evaluate_calibration(
        list(sample.probabilities), [float(x) for x in sample.labels], sample.model_id
    )
    return {
        "total_feedback_events": outcomes_ledger.count(),
        "uncalibrated_discrepancies": None,
        "shadow_model_brier_score": report.brier_score,
        "calibration_drift_detected": report.is_drift_detected,
    }


def _build_contract_state(  # noqa: C901, PLR0912, PLR0915
    role_str: str, operator_id: str | None = None, entity_id: str | None = None
) -> dict[str, Any]:
    """Compiles the full CockpitUiContract JSON structure for a role (read-only, side-effect free)."""
    norm_role = role_str.lower().strip()
    now_iso = _get_utc_now()
    case_extras: dict[str, Any] = {}  # what the AML engine view adds around its dossier

    if norm_role in ("executive", "ceo", "cro"):
        role_enum = "executive"
        briefing = executive_svc.get_morning_briefing()
        dag = executive_svc.get_causal_dag()

        engine_exec = executive_engine_service()
        triage_items = (
            engine_exec.triage_items(now_iso)
            if engine_exec is not None
            else [
                {
                    "id": "item_comp_1",
                    "title": "Spread Shock LatAm Indices",
                    "subtitle": "18 bps widening on top 3 brokers",
                    "entity_id": "COMP-LATAM-01",
                    "priority_score": 0.94,
                    "severity": "HIGH",
                    "status": "OPEN",
                    "timestamp": now_iso,
                },
                {
                    "id": "item_part_2",
                    "title": "Partner AP-1029 Decay Alert",
                    "subtitle": "Login decay 68% following rival bonus",
                    "entity_id": "AP-1029",
                    "priority_score": 0.88,
                    "severity": "CRITICAL",
                    "status": "OPEN",
                    "timestamp": now_iso,
                },
                {
                    "id": "item_aml_3",
                    "title": "Syndicate Micro-Turnover Flag",
                    "subtitle": "23 accounts matched micro-timing",
                    "entity_id": "SYN-MULE-14",
                    "priority_score": 0.79,
                    "severity": "MEDIUM",
                    "status": "INVESTIGATING",
                    "timestamp": now_iso,
                },
                {
                    "id": "item_fin_4",
                    "title": "Monthly EBITDA Forecast Pacing",
                    "subtitle": "$3.82M projected vs $3.75M target",
                    "entity_id": "EBITDA-2026-10",
                    "priority_score": 0.65,
                    "severity": "LOW",
                    "status": "RESOLVED",
                    "timestamp": now_iso,
                },
            ]
        )

        active_dossier = {
            "dossier_id": briefing.briefing_id,
            "entity_id": "ENTERPRISE-GLOBAL",
            "headline": "Executive Morning Briefing & Cross-Horizon Causal Propagation",
            "executive_summary": engine_exec.summary()
            if engine_exec is not None
            else "4-horizon synthesis indicating stable revenue pacing with elevated partner poaching risks in LatAm.",
            "sections": [
                {
                    "section_id": f"sec_{h.horizon_name.lower()}",
                    "title": f"{h.horizon_name} Horizon",
                    "narrative_text": h.headline,
                    "citations": [h.primary_metric_id],
                    "metrics": [
                        {
                            "metric_id": h.primary_metric_id,
                            "formatted_value": format_metric(h.primary_metric_id, h.observed_value),
                            "raw_value": h.observed_value,
                            "semantic_definition_version": h.provenance.definition_version,
                            "as_of_timestamp": h.provenance.as_of_timestamp.isoformat(),
                            "origin_engine": h.provenance.computation_source,
                            "steward_role": h.provenance.owner_role,
                            "citation": "[COMPUTED]" if engine_exec is not None else "[BRIEF]",
                        }
                    ],
                }
                for h in briefing.horizons
            ],
            "as_of_timestamp": now_iso,
            "is_cached_snapshot": briefing.is_cached_fallback,
        }

        kinetic_canvas = {
            "canvas_type": "CAUSAL_DAG",
            "payload": {
                "nodes": [n.model_dump() for n in dag.nodes],
                "edges": [
                    {
                        "source": e.source_node_id,
                        "target": e.target_node_id,
                        "weight": e.weight,
                        "is_causal_verified": e.refuter.is_causal_verified,
                        "confidence": e.refuter.confidence,
                        "placebo_p_value": e.refuter.placebo_p_value,
                        "status_label": e.refuter.status_label,
                    }
                    for e in dag.edges
                ],
            },
        }

    elif norm_role in AML_ROLES and engine_service() is not None:
        role_enum = "aml_investigator"
        engine = cast(EngineAMLService, engine_service())
        chosen = (
            entity_id if entity_id and engine.supports_detail(entity_id) else default_entity(engine)
        )
        case = aml_view.case_payload(engine, chosen)
        triage_items = aml_view.triage_items(engine, now_iso)
        active_dossier = case["active_dossier"]
        kinetic_canvas = case["kinetic_canvas"]
        case_extras = {k: case[k] for k in ("evidence_strip", "sar_draft", "case_actions")}

    elif norm_role in ("aml_investigator", "aml", "compliance_aml"):
        role_enum = "aml_investigator"
        queue = aml_svc.get_triage_queue(min_score=50, limit=10)
        dossier = aml_svc.get_entity_dossier("CR84920")
        graph = aml_svc.get_kinetic_network_graph(entity_id="CR84920", hub_threshold=100)
        sar = aml_svc.compose_sar_draft(case_id="case_aml_84920", entity_id="CR84920")

        triage_items = [
            {
                "id": q["alert_id"],
                "title": f"AML Alert {q['entity_id']}",
                "subtitle": q["discrepancy_summary"],
                "entity_id": q["entity_id"],
                "priority_score": round(q["risk_score"] / 100.0, 2),
                "severity": "CRITICAL"
                if q["risk_score"] >= 80
                else ("HIGH" if q["risk_score"] >= 65 else "MEDIUM"),
                "status": "OPEN" if q["status"] == "UNREVIEWED" else "INVESTIGATING",
                "timestamp": now_iso,
            }
            for q in queue
        ]

        active_dossier = {
            "dossier_id": f"dos_{dossier.entity_id}",
            "entity_id": dossier.entity_id,
            "headline": f"AML Investigation Dossier - Entity {dossier.entity_id}",
            "executive_summary": "High-velocity round-trip turnover with declared income mismatch and shared device cluster.",
            "sections": [
                {
                    "section_id": "sec_kyc",
                    "title": "KYC & Income Declarations",
                    "narrative_text": f"Entity registered in {dossier.kyc.country_of_residence} as {dossier.kyc.employment_status}. Declared income ${dossier.kyc.declared_monthly_income_usd:.0f}/mo.",
                    "citations": ["declared_monthly_income_usd"],
                    "metrics": [
                        {
                            "metric_id": "declared_monthly_income_usd",
                            "formatted_value": f"${dossier.kyc.declared_monthly_income_usd:,.0f}/mo",
                            "raw_value": dossier.kyc.declared_monthly_income_usd,
                            "semantic_definition_version": "v2.1",
                            "as_of_timestamp": now_iso,
                            "origin_engine": "KYCOntologyService",
                            "steward_role": "AMLComplianceSteward",
                            "citation": "[BRIEF]",
                        }
                    ],
                },
                {
                    "section_id": "sec_velocity",
                    "title": "Transaction Velocity & Micro-PnL",
                    "narrative_text": f"Observed 30-day volume ${dossier.discrepancy.realized_deposit_volume_30d_usd:,.0f} vs declared income ${dossier.kyc.declared_monthly_income_usd:.0f}. Discrepancy multiplier {dossier.discrepancy.discrepancy_multiplier:.1f}x.",
                    "citations": ["realized_deposit_volume_30d_usd"],
                    "metrics": [
                        {
                            "metric_id": "realized_deposit_volume_30d_usd",
                            "formatted_value": f"${dossier.discrepancy.realized_deposit_volume_30d_usd:,.0f}",
                            "raw_value": dossier.discrepancy.realized_deposit_volume_30d_usd,
                            "semantic_definition_version": dossier.discrepancy.provenance.definition_version,
                            "as_of_timestamp": dossier.discrepancy.provenance.as_of_timestamp.isoformat(),
                            "origin_engine": dossier.discrepancy.provenance.computation_source,
                            "steward_role": dossier.discrepancy.provenance.owner_role,
                            "citation": "[SPIKE]",
                        }
                    ],
                },
                {
                    "section_id": "sec_sar_draft",
                    "title": "Near-Final SAR Draft Narrative",
                    "narrative_text": sar.narrative_summary,
                    "citations": ["finCEN_form_111", "rule_314a"],
                    "metrics": [],
                },
            ],
            "as_of_timestamp": now_iso,
            "is_cached_snapshot": False,
        }

        kinetic_canvas = {
            "canvas_type": "TOPOLOGICAL_GRAPH",
            "payload": {
                "nodes": [n.model_dump() for n in graph.nodes],
                "edges": [e.model_dump() for e in graph.edges],
                "cgnat_suppressed": True,
                "hub_count_suppressed": 3,
            },
        }

    elif norm_role in PARTNER_ROLES and partner_engine_service() is not None:
        role_enum = "partner_manager"
        psvc = cast(EnginePartnerService, partner_engine_service())
        chosen = (
            entity_id
            if entity_id and psvc.has_detail(entity_id)
            else partner_view.default_partner(psvc)
        )
        case = partner_view.case_payload(psvc, chosen)
        triage_items = partner_view.triage_items(psvc, now_iso)
        active_dossier = case["active_dossier"]
        kinetic_canvas = case["kinetic_canvas"]

    elif norm_role in PARTNER_ROLES:
        role_enum = "partner_manager"
        radar = partner_svc.get_churn_radar_scatter()
        playbooks = partner_svc.get_retention_playbooks("AP-1029")

        triage_items = [
            {
                "id": f"item_{p.partner_id}",
                "title": f"Partner {p.partner_id}",
                "subtitle": p.primary_root_cause,
                "entity_id": p.partner_id,
                "priority_score": p.churn_hazard_probability,
                "severity": "CRITICAL"
                if p.churn_hazard_probability >= 0.8
                else ("HIGH" if p.churn_hazard_probability >= 0.5 else "MEDIUM"),
                "status": "OPEN",
                "timestamp": now_iso,
            }
            for p in radar.partners
        ]

        active_dossier = {
            "dossier_id": "dos_partner_radar",
            "entity_id": "AP-1029",
            "headline": "Partner Hazard Radar & 3-Tier Sub-Affiliate Breakdown",
            "executive_summary": "Top LatAm introducing broker AP-1029 experiencing login and turnover decay following rival poaching.",
            "sections": [
                {
                    "section_id": "sec_decay",
                    "title": "Decay Diagnostics (AP-1029)",
                    "narrative_text": "Login activity declined -68.0% over 14 days. First-time deposits dropped -45.0%. Competitive spread telemetry indicates poaching attempts.",
                    "citations": ["churn_hazard_probability"],
                    "metrics": [
                        {
                            "metric_id": "churn_hazard_probability",
                            "formatted_value": "84.0%",
                            "raw_value": 0.84,
                            "semantic_definition_version": "v1.2",
                            "as_of_timestamp": now_iso,
                            "origin_engine": "PartnerChurnHazardEngine",
                            "steward_role": "PartnerOperationsSteward",
                            "citation": "[TARGET]",
                        }
                    ],
                },
                {
                    "section_id": "sec_playbooks",
                    "title": "Recommended Retention Playbooks",
                    "narrative_text": f"Recommended playbook: {playbooks[0].title if playbooks else 'VIP Spread Rebate Deal'}. Projected uplift +{playbooks[0].projected_retention_uplift_pct if playbooks else 24.5}% retention.",
                    "citations": ["payout_rate"],
                    "metrics": [],
                },
            ],
            "as_of_timestamp": now_iso,
            "is_cached_snapshot": False,
        }

        kinetic_canvas = {
            "canvas_type": "CHURN_RADAR",
            "payload": {
                "partners": [p.model_dump() for p in radar.partners],
                "affiliate_tree": {
                    "master_partner_id": "AP-1029",
                    "sub_affiliates": [
                        {
                            "id": "SUB-101",
                            "name": "Bogota Trading Desk",
                            "volume_usd": 420000.0,
                            "co_occurrence_pct": 92.4,
                            "flagged_mirror_trading": True,
                        },
                        {
                            "id": "SUB-102",
                            "name": "Medellin Retail Hub",
                            "volume_usd": 380000.0,
                            "co_occurrence_pct": 34.0,
                            "flagged_mirror_trading": False,
                        },
                        {
                            "id": "SUB-103",
                            "name": "Lima FX Group",
                            "volume_usd": 440000.0,
                            "co_occurrence_pct": 88.1,
                            "flagged_mirror_trading": True,
                        },
                    ],
                },
            },
        }

    elif norm_role in ("compliance_auditor", "compliance", "audit"):
        role_enum = "compliance_auditor"
        triage_items, active_dossier, kinetic_canvas = compliance_view.workstation(
            compliance_svc, now_iso
        )

    elif (
        operations_engine_service() is not None
    ):  # data_operations / platform_ops on the engine plane
        role_enum = "data_operations"
        triage_items, active_dossier, kinetic_canvas = operations_view.workstation(
            cast(EngineOperationsService, operations_engine_service()), now_iso
        )

    else:  # data_operations / platform_ops
        role_enum = "data_operations"
        products = operations_svc.get_data_products()
        sla_statuses = [p.to_contract_dict() for p in products]
        err_budgets = [
            {
                "slo_id": "SLO-1",
                "name": "Streaming Ingestion Lag (<30s)",
                "consumed_pct": 24.2,
                "status": "HEALTHY",
            },
            {
                "slo_id": "SLO-2",
                "name": "Metric Calculation Determinism",
                "consumed_pct": 0.0,
                "status": "HEALTHY",
            },
            {
                "slo_id": "SLO-3",
                "name": "DoWhy Refuter Confidence",
                "consumed_pct": 12.5,
                "status": "HEALTHY",
            },
            {
                "slo_id": "SLO-4",
                "name": "CGNAT False Positive Suppression",
                "consumed_pct": 8.0,
                "status": "HEALTHY",
            },
            {
                "slo_id": "SLO-5",
                "name": "WORM Immutability Verification",
                "consumed_pct": 0.0,
                "status": "HEALTHY",
            },
            {
                "slo_id": "SLO-6",
                "name": "Sub-200ms Parametric Propagation",
                "consumed_pct": 18.0,
                "status": "HEALTHY",
            },
            {
                "slo_id": "SLO-7",
                "name": "Sub-50ms Metric Popover Egress",
                "consumed_pct": 14.0,
                "status": "HEALTHY",
            },
            {
                "slo_id": "SLO-8",
                "name": "DLQ Quarantine Depth (<10 msgs)",
                "consumed_pct": 0.0,
                "status": "HEALTHY",
            },
            {
                "slo_id": "SLO-9",
                "name": "KMS Key Rotation Proof Validity",
                "consumed_pct": 0.0,
                "status": "HEALTHY",
            },
            {
                "slo_id": "SLO-10",
                "name": "Four-Eyes Dual Approval Audit",
                "consumed_pct": 0.0,
                "status": "HEALTHY",
            },
        ]
        red_lines = [
            {
                "gate_id": "RL-1",
                "name": "Metric Calculation Determinism",
                "status": "PASS",
                "margin_delta": 0.0,
            },
            {
                "gate_id": "RL-2",
                "name": "Four-Eyes Enforcement Integrity",
                "status": "PASS",
                "margin_delta": 0.0,
            },
            {
                "gate_id": "RL-3",
                "name": "DoWhy Refuter Confidence Threshold",
                "status": "PASS",
                "margin_delta": 0.12,
            },
            {
                "gate_id": "RL-4",
                "name": "CGNAT Hub False-Positive Suppression",
                "status": "PASS",
                "margin_delta": 0.05,
            },
            {
                "gate_id": "RL-5",
                "name": "WORM Retention Lock Immutable Anchoring",
                "status": "PASS",
                "margin_delta": 0.0,
            },
            {
                "gate_id": "RL-6",
                "name": "Sub-200ms Parametric Propagation",
                "status": "PASS",
                "margin_delta": -145.2,
            },
            {
                "gate_id": "RL-7",
                "name": "Sub-50ms Metric Popover Egress",
                "status": "PASS",
                "margin_delta": -32.8,
            },
        ]

        triage_items = [
            {
                "id": f"item_dp_{p.product_name}",
                "title": f"Data Product {p.product_name}",
                "subtitle": f"SLA: {p.freshness_sla_seconds}s | Quality: {p.null_check_pass_rate * 100:.2f}% | Status: {p.status.value}",
                "entity_id": p.product_name,
                "priority_score": 0.85 if p.is_degraded else 0.2,
                "severity": "CRITICAL" if p.is_degraded else "LOW",
                "status": "OPEN" if p.is_degraded else "RESOLVED",
                "timestamp": now_iso,
            }
            for p in products
        ]

        total_products = len(products)
        breached_products = [p for p in products if p.status.value == "BREACHED"]
        degraded_products = [p for p in products if p.status.value == "DEGRADED"]
        if breached_products:
            names = ", ".join(p.product_name for p in breached_products)
            health_summary = f"{len(breached_products)} of {total_products} data products breached freshness SLA ({names})."
        elif degraded_products:
            health_summary = f"{len(degraded_products)} of {total_products} data products degraded."
        else:
            health_summary = f"All {total_products} data products meeting freshness SLAs."
        passing_gates = sum(1 for g in red_lines if g["status"] == "PASS")
        budgets_healthy = all(b["status"] == "HEALTHY" for b in err_budgets)
        budget_narrative = (
            f"All {len(err_budgets)} error budgets are within 30-day thresholds."
            if budgets_healthy
            else "One or more error budgets are outside 30-day thresholds; see the SLO board."
        )

        active_dossier = {
            "dossier_id": "dos_data_ops",
            "entity_id": "PLATFORM-OPERATIONS",
            "headline": "Real-Time Data Platform Operations & 10-SLO Engine Monitor",
            "executive_summary": (
                f"{health_summary} {passing_gates} of {len(red_lines)} red-line gates passing."
            ),
            "sections": [
                {
                    "section_id": "sec_slos",
                    "title": "Continuous 10-SLO Status & Error Budget",
                    "narrative_text": budget_narrative,
                    "citations": ["streaming_lag_ms"],
                    "metrics": [
                        {
                            "metric_id": "streaming_lag_seconds",
                            "formatted_value": "18.4s",
                            "raw_value": 18.4,
                            "semantic_definition_version": "v3.0",
                            "as_of_timestamp": now_iso,
                            "origin_engine": "StreamMonitorEngine",
                            "steward_role": "PlatformEngineer",
                            "citation": "[TARGET]",
                        }
                    ],
                }
            ],
            "as_of_timestamp": now_iso,
            "is_cached_snapshot": False,
        }

        kinetic_canvas = {
            "canvas_type": "OPERATIONS_SLO",
            "payload": {
                "sla_statuses": sla_statuses,
                "error_budgets": err_budgets,
                "red_line_gates": red_lines,
            },
        }

    # Staged action cards formatted for UI contract
    raw_cards = action_shelf.list_cards()
    formatted_cards = []
    for c in raw_cards:
        tok = action_shelf.get_token(c.intent_id)
        formatted_cards.append(_card_to_ui_contract_dict(c, tok))

    # Build full contract JSON conforming to cockpit-ui-contract.schema.json
    contract_payload: dict[str, Any] = {
        **case_extras,
        "session": {
            "session_id": f"sess_{role_enum}_{int(time.time())}",
            "active_role": role_enum,
            "operator_id": operator_id or "OPERATOR_EIOS_LEAD",
            "clearance_level": "LEVEL_3_EXECUTIVE" if role_enum == "executive" else "LEVEL_2",
            "timestamp": now_iso,
        },
        "triage_queue": {
            "total_count": len(triage_items),
            "selected_item_id": triage_items[0]["id"] if triage_items else None,
            "items": triage_items,
        },
        "active_dossier": active_dossier,
        "kinetic_canvas": kinetic_canvas,
        "governed_action_shelf": {
            "staged_count": len(formatted_cards),
            "actions": formatted_cards,
        },
        "fallback_state": {
            "is_active": False,
            "badge_label": _data_badge(role_enum),
            "cached_timestamp": None,
            "outage_reason": None,
        },
        "copilot_command_bar": {
            "is_active": True,
            "active_query": "",
            "last_auditor_status": "PASS",
        },
        "flywheel_status": _flywheel_status(),
        "dr_proofs": [
            {
                "runbook_id": "DR-KMS-ROT-001",
                "runbook_name": "Cloud KMS Keyring Automated Rotation",
                "verification_status": "PASS",
                "kms_keyring_rotation_status": "ACTIVE_ROTATED",
                "backup_checkpoint_hash": hashlib.sha256(
                    b"DR_KMS_BACKUP_CHECKPOINT_2026"
                ).hexdigest(),
            },
            {
                "runbook_id": "DR-WARM-CACHE-002",
                "runbook_name": "Warm-Start Snapshot Cache Pre-warming",
                "verification_status": "PASS",
                "kms_keyring_rotation_status": "VERIFIED_VALID",
                "backup_checkpoint_hash": hashlib.sha256(b"WARM_CACHE_CHECKPOINT_2026").hexdigest(),
            },
        ],
        "red_line_gates": [
            {
                "gate_id": "RL-1",
                "name": "Metric Calculation Determinism",
                "status": "PASS",
                "margin_delta": 0.0,
            },
            {
                "gate_id": "RL-2",
                "name": "Four-Eyes Enforcement Integrity",
                "status": "PASS",
                "margin_delta": 0.0,
            },
            {
                "gate_id": "RL-3",
                "name": "DoWhy Refuter Confidence Threshold",
                "status": "PASS",
                "margin_delta": 0.12,
            },
            {
                "gate_id": "RL-4",
                "name": "CGNAT Hub False-Positive Suppression",
                "status": "PASS",
                "margin_delta": 0.05,
            },
            {
                "gate_id": "RL-5",
                "name": "WORM Retention Lock Immutable Anchoring",
                "status": "PASS",
                "margin_delta": 0.0,
            },
            {
                "gate_id": "RL-6",
                "name": "Sub-200ms Parametric Propagation",
                "status": "PASS",
                "margin_delta": -145.2,
            },
            {
                "gate_id": "RL-7",
                "name": "Sub-50ms Metric Popover Egress",
                "status": "PASS",
                "margin_delta": -32.8,
            },
        ],
    }

    ops_engine = operations_engine_service()
    if ops_engine is not None:
        contract_payload["dr_proofs"] = operations_view.dr_proofs(ops_engine)
        contract_payload["red_line_gates"] = operations_view.red_line_payload(ops_engine)

    return contract_payload


HEALTH_PATH = "/health"
API_HEALTH_PATH = "/api/health"
WORKSTATIONS_PATH = "/api/cockpit/workstations/{role}"
SIMULATE_PATH = "/api/cockpit/simulate"
EXECUTIVE_BOARD_PATH = "/api/cockpit/executive"
STAGE_ACTION_PATH = "/api/cockpit/actions/stage"
AUTHORIZE_ACTION_PATH = "/api/cockpit/actions/authorize"
PARTNER_CASE_PATH = "/api/cockpit/partners/{entity_id}"
AML_CASE_PATH = "/api/cockpit/aml/cases/{entity_id}"
COPILOT_QUERY_PATH = "/api/cockpit/copilot/query"
COPILOT_MODELS_PATH = "/api/cockpit/copilot/models"
FLYWHEEL_FEEDBACK_PATH = "/api/cockpit/flywheel/feedback"
AUDIT_VERIFY_PATH = "/api/cockpit/audit/verify"
COMPLIANCE_LEDGER_PATH = "/api/cockpit/compliance/ledger"

public_router = APIRouter(tags=["Cockpit Presentation"])
router = APIRouter(tags=["Cockpit Presentation"], dependencies=[Depends(current_operator)])


# Endpoints
@public_router.get(HEALTH_PATH, response_model=CockpitHealthResponse)
@public_router.get(API_HEALTH_PATH, response_model=CockpitHealthResponse)
def get_health() -> CockpitHealthResponse:
    return CockpitHealthResponse(
        status="UP",
        version=API_VERSION,
        service="EIOS Presentation Engine",
        engine="EIOS Presentation Engine",
        design_system="EIOS Sovereign Design Tokens (Light Mode)",
        security_standard="Google Cloud KMS ECDSA P-256",
        sse_enabled=True,
        cors_configured=True,
        timestamp=_get_utc_now(),
    )


@router.get(WORKSTATIONS_PATH)
def get_workstation_state(
    role: str,
    entity_id: str | None = None,
    operator: Operator | None = Depends(current_operator),
) -> dict[str, Any]:
    """Returns the full contract-compliant client state for the requested workstation.

    `entity_id` selects which case the dossier and canvas open on (the AML workstation); unknown ids fall back to the
    strongest case rather than showing another account's data.
    """
    try:
        return _build_contract_state(
            role, operator_id=operator.uid if operator else None, entity_id=entity_id
        )
    except Exception as exc:
        _LOG.exception("failed to assemble workstation state for %s", role)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assemble workstation state",
        ) from exc


@router.get(AML_CASE_PATH)
def get_aml_case(entity_id: str) -> dict[str, Any]:
    """One account's computed dossier and network canvas, for the selection a browser just made."""
    engine = engine_service()
    if engine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no engine plane")
    if not valid_entity_id(entity_id) or not engine.supports_detail(entity_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such account")
    try:
        return aml_view.case_payload(engine, entity_id)
    except UnknownAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no such account"
        ) from exc


@router.get(PARTNER_CASE_PATH)
def get_partner_case(entity_id: str) -> dict[str, Any]:
    """One partner's computed dossier, radar and referral tree, for the selection a browser just made."""
    psvc = partner_engine_service()
    if psvc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no engine plane")
    if not valid_entity_id(entity_id) or not psvc.has_detail(entity_id.upper()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such partner")
    return partner_view.case_payload(psvc, entity_id.upper())


@router.post(SIMULATE_PATH, response_model=WhatIfSimulationResponse)
def simulate_what_if_shock(req: SimulateRequest) -> WhatIfSimulationResponse:
    """Parametric propagation across structural causal model equations."""
    try:
        result = executive_svc.simulate_what_if_shock(
            shock_param=req.shock_param,
            magnitude_pct=req.magnitude_pct,
        )
    except ValueError as exc:  # a shock with no tested causal path is refused, not simulated
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return WhatIfSimulationResponse(**result)


@router.get(EXECUTIVE_BOARD_PATH)
def get_executive_board() -> dict[str, Any]:
    """The executive board: briefing, forecast with its measured interval, causal graph and the shocks on offer."""
    origin = "engine" if executive_engine_service() is not None else "fixture"
    return exec_view.board_payload(executive_svc, origin)


# The cockpit and the cards contract use some names the ontology spells differently.
_ACTION_ALIASES = {
    "DeployRetentionVIPDeal": "DeployRetentionConcession",
    "DEPLOY_RETENTION_PLAYBOOK": "DeployRetentionConcession",
}


def _resolve_parameters(
    action_type: str, target_entity_id: str, metadata: dict[str, Any]
) -> dict[str, Any]:
    """Fill the action's first missing required *_id parameter from the target entity."""
    params = dict(metadata)
    spec = CANONICAL_ACTION_SPECS.get(action_type)
    if spec:
        for required in spec["required_params"]:
            if required.endswith("_id") and required not in params:
                params[required] = target_entity_id
                break
    return params


@router.post(STAGE_ACTION_PATH, response_model=StageActionResponse)
def stage_governed_action(
    req: StageActionRequest,
    operator: Operator | None = Depends(require_roles(STAGE_ROLES)),  # noqa: B008
) -> StageActionResponse:
    """Propose an action through the intent hub: validated, KMS-signed, nonce-registered and ledgered."""
    action_type = _ACTION_ALIASES.get(req.action_type, req.action_type)
    requester = operator.uid if operator else (req.initiator_officer_id or "DEV_OPERATOR")
    try:
        token = governance.hub.propose_action(
            action_type=action_type,
            parameters=_resolve_parameters(action_type, req.target_entity_id, req.metadata),
            evidence_refs=["ev_user_staged"],
            requester_agent_id=requester,
            policy_tags=["STAGED_VIA_COCKPIT"],
            require_dual_approval=req.requires_four_eyes,
        )
    except InvalidActionParameterError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    card = action_shelf.present_card(token)
    return StageActionResponse(
        status="STAGED",
        card=_card_to_ui_contract_dict(card, token),
        total_staged=len(action_shelf.list_cards()),
    )


@router.post(AUTHORIZE_ACTION_PATH, response_model=AuthorizeActionResponse)
def authorize_governed_action(
    req: AuthorizeActionRequest,
    operator: Operator | None = Depends(require_roles(APPROVE_ROLES)),  # noqa: B008
) -> AuthorizeActionResponse:
    """Record a Four-Eyes approval; commit the action once every required approval is in."""
    try:
        card = action_shelf.submit_approval(
            intent_id=req.intent_id,
            approver_id=operator.uid if operator else req.authorizer_id,
            approver_role=operator.role if operator else "COMPLIANCE_OFFICER",
            comment="Authorized via Cockpit Governed Action Shelf",
        )
        if card.status == "APPROVED":
            action_shelf.execute_action(req.intent_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Staged action {req.intent_id} not found"
        ) from exc
    except (FourEyesViolationError, InvalidActionParameterError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ConcurrentModificationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    token = action_shelf.get_token(req.intent_id)
    final_card = action_shelf.present_card(token) if token else card
    if final_card.status == "EXECUTED":
        outcome = "COMMITTED"
    elif final_card.status == "APPROVED":
        outcome = "APPROVED"
    else:
        outcome = "PENDING_SECOND_EYE"
    return AuthorizeActionResponse(
        status=outcome,
        card=_card_to_ui_contract_dict(final_card, token),
        committed_timestamp=_get_utc_now(),
    )


@router.get(COPILOT_MODELS_PATH)
async def copilot_models() -> dict[str, Any]:
    """The models an operator may pick for the assistant: key, label, note, and which one is the default. No ids."""
    try:
        runtime = await run_in_threadpool(get_runtime)
    except AssistantConfigError as exc:
        logging.getLogger(__name__).error("assistant is not configured: %s", exc)
        raise HTTPException(status_code=503, detail="offline") from exc
    return {"models": runtime.registry.public()}


@router.post(COPILOT_QUERY_PATH, dependencies=[Depends(limit_copilot)])
async def query_copilot(
    req: CopilotQueryRequest, operator: Operator | None = Depends(current_operator)
) -> dict[str, Any]:
    """Processes Copilot queries with Metric Auditor Gate verification and dual-engine grounding.

    Identity is the verified operator; the workstation is only the scope they ask to work in, and an unknown one is
    refused rather than widened to a default. The session belongs to the operator, so memory is never shared.
    """
    try:
        principal = principal_for(operator.uid if operator else None, req.role.strip().lower())
    except PortError as exc:
        raise HTTPException(status_code=422, detail=exc.error.message) from exc

    if not valid_entity_id(req.context_entity_id):
        raise HTTPException(status_code=422, detail="activeEntityId is not a valid identifier")
    try:
        runtime = await run_in_threadpool(get_runtime)
    except AssistantConfigError as exc:
        logging.getLogger(__name__).error("assistant is not configured: %s", exc)
        raise HTTPException(status_code=503, detail="offline") from exc
    try:
        outcome = await runtime.run_turn(
            principal=principal,
            question=req.query,
            entity_id=req.context_entity_id,
            model_key=req.model,
        )
    except UnknownModelError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record_turn(read_models().slo_engine, outcome)
    if outcome.status != "ok":  # an outage is offline, never a 200 that looks like an answer
        return JSONResponse(  # type: ignore[return-value]
            status_code=503,
            content={"detail": "offline", **assistant_response_body(req.query, outcome)},
        )
    return assistant_response_body(req.query, outcome)


@router.post(FLYWHEEL_FEEDBACK_PATH, response_model=FlywheelFeedbackResponse)
def submit_flywheel_feedback(
    req: FlywheelFeedbackRequest, operator: Operator | None = Depends(current_operator)
) -> FlywheelFeedbackResponse:
    """Records operator annotation/revision into closed-loop Decision Outcomes Ledger."""
    decision_id = f"dec_{int(time.time() * 1000)}"
    now = datetime.now(UTC)
    propensity = req.propensity_score if req.propensity_score is not None else 0.92
    annotator = operator.uid if operator else (req.annotator_id or "OPERATOR_FEEDBACK")
    record = DecisionOutcomeRecord(
        decision_id=decision_id,
        intent_id=f"intent_{req.case_id}",
        timestamp=now,
        service_name="aml_investigator_workstation",
        action_type=req.feedback_type,
        entity_type="InvestigationCase",
        entity_id=req.case_id,
        propensity_score=propensity,
        treatment_assigned=not req.false_positive,
        covariates={"annotator": annotator},
        predicted_impact_30d=0.0,
        predicted_impact_60d=0.0,
        predicted_impact_90d=0.0,
        provenance_hash="AUTO",
    )
    outcomes_ledger.append_decision(record)

    return FlywheelFeedbackResponse(
        status="RECORDED",
        decision_id=decision_id,
        provenance_hash=record.provenance_hash,
        total_flywheel_records=outcomes_ledger.count(),
        timestamp=_get_utc_now(),
    )


@router.get(AUDIT_VERIFY_PATH, response_model=AuditVerifyResponse)
def verify_ledger_continuity() -> AuditVerifyResponse:
    """Walk the real decision ledger: sequence continuity, SHA-256 hash chain and signed checkpoints."""
    report = ContinuousAuditWalker(governance.sequencer, governance.worm).verify_ledger()
    checkpoints = governance.worm.get_checkpoints()
    return AuditVerifyResponse(
        status="VALID" if report.is_valid else "TAMPERED",
        total_records=report.total_entries,
        last_hash=report.head_hash,
        genesis_hash=report.genesis_hash,
        tampered_sequence_id=report.tampered_sequence_id,
        failure_reason=report.failure_reason,
        worm_checkpoints_verified=report.worm_checkpoints_verified,
        # Checkpoints are signed at the application level; no bucket retention lock is claimed here.
        worm_mode="SIGNED_CHECKPOINTS" if checkpoints else "NO_CHECKPOINTS",
        audit_duration_ms=report.audit_duration_ms,
        verified_at=_get_utc_now(),
    )


@router.get(COMPLIANCE_LEDGER_PATH)
def compliance_ledger() -> dict[str, Any]:
    """The decision ledger as the auditor reads it: entries, sign-offs, signed checkpoints and an audit walk."""
    return compliance_view.ledger_payload(compliance_svc)


app.include_router(public_router)
app.include_router(router)
app.include_router(geo_routes.router)


def main() -> None:
    parser = argparse.ArgumentParser(description="EIOS Cockpit Presentation Gateway")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind to")  # noqa: S104
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
