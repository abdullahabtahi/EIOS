"""FastAPI Cockpit API Gateway.

Wraps the Cockpit Presentation Engine and underlying services:
- CockpitShellPresenter
- ExecutiveCockpitService
- AMLWorkstationService
- PartnerWorkstationService
- ComplianceExplorerService
- DataPlatformOperationsService
- GovernedActionShelf
- MetricAuditorGate
- DecisionOutcomesLedger

Serves full contract-compliant JSON payloads adhering to
specs/016-cockpit-frontend/contracts/cockpit-ui-contract.schema.json.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import time
from datetime import UTC, datetime
from typing import Any

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from eios.assistant.config import AssistantConfigError
from eios.cockpit.aml import AMLWorkstationService
from eios.cockpit.assistant_gateway import (
    assistant_enabled,
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
from eios.cockpit.compliance import ComplianceExplorerService
from eios.cockpit.executive import ExecutiveCockpitService
from eios.cockpit.governance_runtime import build_governance_runtime
from eios.cockpit.governance_shelf import GovernedActionCard
from eios.cockpit.operations import DataPlatformOperationsService
from eios.cockpit.partner import PartnerWorkstationService
from eios.cockpit.session import SessionManager
from eios.cockpit.shell import CockpitShellPresenter
from eios.conversation.copilot_engine import CopilotEngine
from eios.conversation.models import OperatorRole as EngineOperatorRole
from eios.flywheel.ledger import DecisionOutcomeRecord, DecisionOutcomesLedger
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
from eios.ontology.auditor.gate import MetricAuditorGate
from eios.ontology.omcp.port.contracts import PortError
from eios.ontology.omcp.port.principal import principal_for

_LOG = logging.getLogger("eios.cockpit.server")

copilot_engine = CopilotEngine()

app = FastAPI(
    title="EIOS Cockpit Presentation Gateway",
    version="0.1.0",
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
governance = build_governance_runtime()
action_shelf = governance.shelf
presenter = CockpitShellPresenter(session_manager=session_mgr, action_shelf=action_shelf)
executive_svc = ExecutiveCockpitService()
aml_svc = AMLWorkstationService()
partner_svc = PartnerWorkstationService()
compliance_svc = ComplianceExplorerService()
operations_svc = DataPlatformOperationsService()
auditor_gate = MetricAuditorGate(relative_tolerance=0.01)
outcomes_ledger = DecisionOutcomesLedger()


# Request/Response Models
class SimulateRequest(BaseModel):
    shock_param: str = "competitor_commission_bps"
    magnitude_pct: float = 25.0


class StageActionRequest(BaseModel):
    action_type: str
    target_entity_id: str
    severity: str = "HIGH"
    initiator_officer_id: str = "OFFICER_CHENG_772"
    requires_four_eyes: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthorizeActionRequest(BaseModel):
    intent_id: str
    authorizer_id: str
    second_eye_token: str | None = None


class CopilotQueryRequest(BaseModel):
    """`activeEntityId` is the name the browser sends today; both names are accepted until the browser is aligned."""

    model_config = ConfigDict(populate_by_name=True)

    query: str
    context_entity_id: str | None = Field(
        default=None, validation_alias=AliasChoices("context_entity_id", "activeEntityId")
    )
    role: str = "executive"


class FlywheelFeedbackRequest(BaseModel):
    case_id: str
    feedback_type: str = "SAR_NARRATIVE_EDIT"
    original_text: str
    revised_text: str
    annotator_id: str = "INVESTIGATOR_ALICE"
    false_positive: bool = False


# Workstation payloads are assembled from in-process fixtures, not from the ingestion pipeline, so the
# contract says so. "[LIVE]" must wait until a state actually arrives from governed data products.
FIXTURE_DATA_BADGE = "[ILLUSTRATIVE]"


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
        "initiator_officer_id": card.first_approver_id or "OFFICER_CHENG_772",
        "second_officer_id": card.second_approver_id,
    }


def _ensure_default_staged_cards() -> None:
    governance.seed_demo_intents()


def _build_contract_state(role_str: str, operator_id: str | None = None) -> dict[str, Any]:  # noqa: PLR0915
    """Compiles the full CockpitUiContract JSON structure for a role."""
    norm_role = role_str.lower().strip()
    now_iso = _get_utc_now()
    _ensure_default_staged_cards()

    if norm_role in ("executive", "ceo", "cro"):
        role_enum = "executive"
        briefing = executive_svc.get_morning_briefing()
        dag = executive_svc.get_causal_dag()

        triage_items = [
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

        active_dossier = {
            "dossier_id": briefing.briefing_id,
            "entity_id": "ENTERPRISE-GLOBAL",
            "headline": "Executive Morning Briefing & Cross-Horizon Causal Propagation",
            "executive_summary": "4-horizon synthesis indicating stable revenue pacing with elevated partner poaching risks in LatAm.",
            "sections": [
                {
                    "section_id": f"sec_{h.horizon_name.lower()}",
                    "title": f"{h.horizon_name} Horizon",
                    "narrative_text": h.headline,
                    "citations": [h.primary_metric_id],
                    "metrics": [
                        {
                            "metric_id": h.primary_metric_id,
                            "formatted_value": f"${h.observed_value:,.0f}"
                            if "usd" in h.primary_metric_id
                            else f"{h.observed_value:,.1f}%",
                            "raw_value": h.observed_value,
                            "semantic_definition_version": h.provenance.definition_version,
                            "as_of_timestamp": h.provenance.as_of_timestamp.isoformat(),
                            "origin_engine": h.provenance.computation_source,
                            "steward_role": h.provenance.owner_role,
                            "citation": "[BRIEF]",
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

    elif norm_role in ("partner_manager", "partner", "growth"):
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
        timeline = compliance_svc.get_ledger_timeline(start_seq=1, limit=10)
        worm_proofs = compliance_svc.get_worm_compliance_proofs()
        primary_worm = (
            worm_proofs[0]
            if worm_proofs
            else {
                "checkpoint_id": "WORM-CKPT-20261009-001",
                "retention_expiration": "2033-10-09T00:00:00+00:00",
                "compliance_lock_mode": "COMPLIANCE",
            }
        )

        triage_items = [
            {
                "id": f"item_seq_{e['ledger_seq']}",
                "title": f"Ledger #{e['ledger_seq']} {e['event_type']}",
                "subtitle": f"Actor: {e['actor_id']} | Hash: {e['current_hash'][:12]}...",
                "entity_id": f"SEQ-{e['ledger_seq']}",
                "priority_score": 0.5,
                "severity": "INFO",
                "status": "RESOLVED",
                "timestamp": e["timestamp"],
            }
            for e in timeline
        ]

        active_dossier = {
            "dossier_id": "dos_compliance_timeline",
            "entity_id": "LEDGER-WORM",
            "headline": "Cryptographic Decision Ledger & WORM Proof Explorer",
            "executive_summary": "Monotonic SHA-256 hash-chain verified. Cloud Storage WORM compliance lock active.",
            "sections": [
                {
                    "section_id": "sec_worm",
                    "title": "WORM Retention Lock Proof",
                    "narrative_text": f"GCS bucket object held under WORM compliance retention until {primary_worm.get('retention_expiration')}. Root hash anchor matches Cloud KMS ECDSA attestation.",
                    "citations": ["worm_checkpoint_id"],
                    "metrics": [
                        {
                            "metric_id": "worm_retention_days",
                            "formatted_value": "2,555 Days Locked",
                            "raw_value": 2555,
                            "semantic_definition_version": "v1.0",
                            "as_of_timestamp": now_iso,
                            "origin_engine": "WORMComplianceService",
                            "steward_role": "ComplianceAuditor",
                            "citation": "[BRIEF]",
                        }
                    ],
                }
            ],
            "as_of_timestamp": now_iso,
            "is_cached_snapshot": False,
        }

        kinetic_canvas = {
            "canvas_type": "LEDGER_TIMELINE",
            "payload": {
                "timeline": timeline,
                "worm_proof": primary_worm,
                "chain_valid": True,
            },
        }

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
            "badge_label": FIXTURE_DATA_BADGE,
            "cached_timestamp": None,
            "outage_reason": None,
        },
        "copilot_command_bar": {
            "is_active": True,
            "active_query": "",
            "last_auditor_status": "PASS",
        },
        "flywheel_status": {
            "total_feedback_events": len(outcomes_ledger._records),
            "uncalibrated_discrepancies": 2,
            "calibration_drift_detected": False,
        },
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

    return contract_payload


HEALTH_PATH = "/health"
API_HEALTH_PATH = "/api/health"
WORKSTATIONS_PATH = "/api/cockpit/workstations/{role}"
SIMULATE_PATH = "/api/cockpit/simulate"
STAGE_ACTION_PATH = "/api/cockpit/actions/stage"
AUTHORIZE_ACTION_PATH = "/api/cockpit/actions/authorize"
COPILOT_QUERY_PATH = "/api/cockpit/copilot/query"
FLYWHEEL_FEEDBACK_PATH = "/api/cockpit/flywheel/feedback"
AUDIT_VERIFY_PATH = "/api/cockpit/audit/verify"

public_router = APIRouter(tags=["Cockpit Presentation"])
router = APIRouter(tags=["Cockpit Presentation"], dependencies=[Depends(current_operator)])


# Endpoints
@public_router.get(HEALTH_PATH)
@public_router.get(API_HEALTH_PATH)
def get_health() -> dict[str, Any]:
    return {
        "status": "UP",
        "version": "0.1.0",
        "engine": "EIOS Presentation Engine",
        "design_system": "EIOS Sovereign Design Tokens (Light Mode)",
        "security_standard": "Google Cloud KMS ECDSA P-256",
        "sse_enabled": True,
        "timestamp": _get_utc_now(),
    }


@router.get(WORKSTATIONS_PATH)
def get_workstation_state(
    role: str, operator: Operator | None = Depends(current_operator)
) -> dict[str, Any]:
    """Returns the full contract-compliant client state for the requested workstation."""
    try:
        return _build_contract_state(role, operator_id=operator.uid if operator else None)
    except Exception as exc:
        _LOG.exception("failed to assemble workstation state for %s", role)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assemble workstation state",
        ) from exc


@router.post(SIMULATE_PATH)
def simulate_what_if_shock(req: SimulateRequest) -> dict[str, Any]:
    """Parametric propagation across structural causal model equations."""
    result = executive_svc.simulate_what_if_shock(
        shock_param=req.shock_param,
        magnitude_pct=req.magnitude_pct,
    )
    return result


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


@router.post(STAGE_ACTION_PATH)
def stage_governed_action(
    req: StageActionRequest,
    operator: Operator | None = Depends(require_roles(STAGE_ROLES)),  # noqa: B008
) -> dict[str, Any]:
    """Propose an action through the intent hub: validated, KMS-signed, nonce-registered and ledgered."""
    action_type = _ACTION_ALIASES.get(req.action_type, req.action_type)
    try:
        token = governance.hub.propose_action(
            action_type=action_type,
            parameters=_resolve_parameters(action_type, req.target_entity_id, req.metadata),
            evidence_refs=["ev_user_staged"],
            requester_agent_id=operator.uid if operator else req.initiator_officer_id,
            policy_tags=["STAGED_VIA_COCKPIT"],
            require_dual_approval=req.requires_four_eyes,
        )
    except InvalidActionParameterError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    card = action_shelf.present_card(token)
    return {
        "status": "STAGED",
        "card": _card_to_ui_contract_dict(card, token),
        "total_staged": len(action_shelf.list_cards()),
    }


@router.post(AUTHORIZE_ACTION_PATH)
def authorize_governed_action(
    req: AuthorizeActionRequest,
    operator: Operator | None = Depends(require_roles(APPROVE_ROLES)),  # noqa: B008
) -> dict[str, Any]:
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
    return {
        "status": outcome,
        "card": _card_to_ui_contract_dict(final_card, token),
        "committed_timestamp": _get_utc_now(),
    }


@router.post(COPILOT_QUERY_PATH)
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

    try:
        use_assistant = assistant_enabled()
        runtime = get_runtime() if use_assistant else None
    except AssistantConfigError as exc:
        logging.getLogger(__name__).error("assistant is not configured: %s", exc)
        raise HTTPException(status_code=503, detail="offline") from exc
    if runtime is not None:
        outcome = await runtime.run_turn(
            principal=principal, question=req.query, entity_id=req.context_entity_id
        )
        return assistant_response_body(req.query, outcome)

    response_model = await run_in_threadpool(
        copilot_engine.process_query,
        query=req.query,
        role=EngineOperatorRole(principal.workstation.value),
        session_id=f"sess_{principal.uid}_{principal.workstation.value}",
    )

    audit = response_model.audit_record
    audit_passed = audit is not None and audit.passed and response_model.auditor_status == "PASS"
    return {
        "query": req.query,
        "response": response_model.response_markdown,
        "auditor_status": response_model.auditor_status or "UNAUDITED",
        "is_replay_fallback": response_model.is_replay_fallback,
        "fallback_reason": response_model.fallback_reason,
        "provenance_citations": [
            {
                "metric_id": c.citation_id,
                "formatted_value": c.label,
                "steward": c.source_engine,
                "as_of": c.as_of.isoformat(),
            }
            for c in response_model.provenance_citations
        ],
        "audit_record": {
            "passed": audit_passed,
            "unanchored_tokens": list(audit.unanchored_tokens) if audit else [],
            "anchored_numbers": list(audit.verified_numerical_anchors) if audit else [],
            "relative_tolerance": audit.relative_tolerance
            if audit
            else auditor_gate.relative_tolerance,
        },
        "tool_trace_count": response_model.tool_trace_count,
        "suggested_action": response_model.staged_recommendation,
        "turn_latency_ms": response_model.turn_latency_ms,
    }


@router.post(FLYWHEEL_FEEDBACK_PATH)
def submit_flywheel_feedback(
    req: FlywheelFeedbackRequest, operator: Operator | None = Depends(current_operator)
) -> dict[str, Any]:
    """Records operator annotation/revision into closed-loop Decision Outcomes Ledger."""
    decision_id = f"dec_{int(time.time() * 1000)}"
    now = datetime.now(UTC)
    record = DecisionOutcomeRecord(
        decision_id=decision_id,
        intent_id=f"intent_{req.case_id}",
        timestamp=now,
        service_name="aml_investigator_workstation",
        action_type=req.feedback_type,
        entity_type="InvestigationCase",
        entity_id=req.case_id,
        propensity_score=0.92,
        treatment_assigned=not req.false_positive,
        covariates={"annotator": operator.uid if operator else req.annotator_id},
        predicted_impact_30d=0.0,
        predicted_impact_60d=0.0,
        predicted_impact_90d=0.0,
        provenance_hash="AUTO",
    )
    outcomes_ledger.append_decision(record)

    return {
        "status": "RECORDED",
        "decision_id": decision_id,
        "provenance_hash": record.provenance_hash,
        "total_flywheel_records": len(outcomes_ledger._records),
        "timestamp": _get_utc_now(),
    }


@router.get(AUDIT_VERIFY_PATH)
def verify_ledger_continuity() -> dict[str, Any]:
    """Walk the real decision ledger: sequence continuity, SHA-256 hash chain and signed checkpoints."""
    report = ContinuousAuditWalker(governance.sequencer, governance.worm).verify_ledger()
    checkpoints = governance.worm.get_checkpoints()
    return {
        "status": "VALID" if report.is_valid else "TAMPERED",
        "total_records": report.total_entries,
        "last_hash": report.head_hash,
        "genesis_hash": report.genesis_hash,
        "tampered_sequence_id": report.tampered_sequence_id,
        "failure_reason": report.failure_reason,
        "worm_checkpoints_verified": report.worm_checkpoints_verified,
        # Checkpoints are signed at the application level; no bucket retention lock is claimed here.
        "worm_mode": "SIGNED_CHECKPOINTS" if checkpoints else "NO_CHECKPOINTS",
        "audit_duration_ms": report.audit_duration_ms,
        "verified_at": _get_utc_now(),
    }


app.include_router(public_router)
app.include_router(router)


def main() -> None:
    parser = argparse.ArgumentParser(description="EIOS Cockpit Presentation Gateway")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind to")  # noqa: S104
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
