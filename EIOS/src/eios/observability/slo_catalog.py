"""Canonical Service Level Objectives (SLO) Catalog and Tier Definitions.

Codifies the 10 production Service Level Objectives from `docs/engagement_plan.md` §2
and Constitution Principle I (Auditor Hallucination Gate), with 28-day rolling evaluation
windows and SRE governance tiers.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SLICategory(str, Enum):
    """Canonical SLI identifiers for all production pipelines and user journeys."""

    INGESTION_FRESHNESS = "ingestion_freshness"
    CONTRACT_ENFORCEMENT = "contract_enforcement"
    METRIC_QUERY_LATENCY = "metric_query_latency"
    AGENT_TURN_FIRST_TOKEN = "agent_turn_first_token"
    AGENT_TURN_FULL_ANSWER = "agent_turn_full_answer"
    ALERT_DOSSIER_ASSEMBLY = "alert_dossier_assembly"
    PRE_WITHDRAWAL_DECISION = "pre_withdrawal_decision"
    MORNING_BRIEFING_AVAILABILITY = "morning_briefing_availability"
    APPROVAL_SERVICE_AVAILABILITY = "approval_service_availability"
    LEDGER_CHAIN_INTEGRITY = "ledger_chain_integrity"
    HALLUCINATION_GATE = "hallucination_gate"


class SLOTier(str, Enum):
    """Operational governance tiers defining budget exhaustion blast radius."""

    TIER_1_CRITICAL = "TIER_1_CRITICAL"  # Depletion triggers automated FEATURE_FREEZE
    TIER_2_OPERATIONAL = "TIER_2_OPERATIONAL"  # Depletion triggers high-priority ticket


class ServiceLevelObjectiveConfig(BaseModel):
    """Configuration specification for a Service Level Objective."""

    sli_name: SLICategory = Field(..., description="Canonical SLI category")
    display_name: str = Field(..., description="Human-readable SLO name")
    description: str = Field(..., description="Operational definition and scope")
    target_percentage: float = Field(
        ..., ge=0.0, le=1.0, description="Target compliance percentage (e.g. 0.995 for 99.5%)"
    )
    target_threshold: float = Field(
        ..., ge=0.0, description="Quantitative SLA boundary (e.g. 30.0 for seconds or 500.0 for ms)"
    )
    unit: str = Field(..., description="Measurement unit (e.g. 'seconds', 'ms', 'pct', 'count')")
    window_days: int = Field(default=28, ge=1, description="Evaluation window duration in days")
    tier: SLOTier = Field(default=SLOTier.TIER_1_CRITICAL, description="Governance severity tier")


# Canonical production catalog of all 10 platform SLOs + Principle I Auditor Gate
DEFAULT_SLO_CATALOG: dict[SLICategory, ServiceLevelObjectiveConfig] = {
    SLICategory.INGESTION_FRESHNESS: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.INGESTION_FRESHNESS,
        display_name="Data Ingestion Freshness",
        description="Freshness lag from source event generation to queryable hot state (p95 <= 30.0s).",
        target_percentage=0.990,
        target_threshold=30.0,
        unit="seconds",
        window_days=28,
        tier=SLOTier.TIER_1_CRITICAL,
    ),
    SLICategory.CONTRACT_ENFORCEMENT: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.CONTRACT_ENFORCEMENT,
        display_name="Contract Enforcement Integrity",
        description="Zero schema violations admitted to hot state; 100% routed to DLQ.",
        target_percentage=1.000,
        target_threshold=0.0,
        unit="count",
        window_days=28,
        tier=SLOTier.TIER_1_CRITICAL,
    ),
    SLICategory.METRIC_QUERY_LATENCY: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.METRIC_QUERY_LATENCY,
        display_name="Metric Query Latency",
        description="Semantic metric resolution latency across hot-state ontology (p95 <= 500.0ms).",
        target_percentage=0.995,
        target_threshold=500.0,
        unit="ms",
        window_days=28,
        tier=SLOTier.TIER_1_CRITICAL,
    ),
    SLICategory.AGENT_TURN_FIRST_TOKEN: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.AGENT_TURN_FIRST_TOKEN,
        display_name="Agent Turn First-Token Latency",
        description="Time-to-first-token in interactive reasoning coordinator turn (p95 <= 3.0s).",
        target_percentage=0.990,
        target_threshold=3.0,
        unit="seconds",
        window_days=28,
        tier=SLOTier.TIER_2_OPERATIONAL,
    ),
    SLICategory.AGENT_TURN_FULL_ANSWER: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.AGENT_TURN_FULL_ANSWER,
        display_name="Agent Turn Full Answer Latency",
        description="Full answer completion time for multi-step agent reasoning turns (p95 <= 20.0s).",
        target_percentage=0.990,
        target_threshold=20.0,
        unit="seconds",
        window_days=28,
        tier=SLOTier.TIER_2_OPERATIONAL,
    ),
    SLICategory.ALERT_DOSSIER_ASSEMBLY: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.ALERT_DOSSIER_ASSEMBLY,
        display_name="Alert Dossier Assembly Latency",
        description="Time required to correlate and assemble alert context dossiers (p95 <= 10.0s).",
        target_percentage=0.990,
        target_threshold=10.0,
        unit="seconds",
        window_days=28,
        tier=SLOTier.TIER_2_OPERATIONAL,
    ),
    SLICategory.PRE_WITHDRAWAL_DECISION: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.PRE_WITHDRAWAL_DECISION,
        display_name="Pre-Withdrawal Evaluation Latency",
        description="Real-time fraud pre-withdrawal scoring latency (p95 <= 2.0s).",
        target_percentage=0.995,
        target_threshold=2.0,
        unit="seconds",
        window_days=28,
        tier=SLOTier.TIER_1_CRITICAL,
    ),
    SLICategory.MORNING_BRIEFING_AVAILABILITY: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.MORNING_BRIEFING_AVAILABILITY,
        display_name="Morning Briefing Availability",
        description="Scheduled daily synthesis briefing delivery by 06:00 UTC (99.0% availability).",
        target_percentage=0.990,
        target_threshold=1.0,
        unit="pct",
        window_days=28,
        tier=SLOTier.TIER_2_OPERATIONAL,
    ),
    SLICategory.APPROVAL_SERVICE_AVAILABILITY: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.APPROVAL_SERVICE_AVAILABILITY,
        display_name="Human Approval Service Availability",
        description="Human-in-the-loop action approval & four-eyes quorum availability (99.5% availability).",
        target_percentage=0.995,
        target_threshold=1.0,
        unit="pct",
        window_days=28,
        tier=SLOTier.TIER_1_CRITICAL,
    ),
    SLICategory.LEDGER_CHAIN_INTEGRITY: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.LEDGER_CHAIN_INTEGRITY,
        display_name="Cryptographic Ledger Chain Integrity",
        description="Strict zero-gap, tamper-evident hash-chain integrity on immutable audit ledger (100.0%).",
        target_percentage=1.000,
        target_threshold=0.0,
        unit="count",
        window_days=28,
        tier=SLOTier.TIER_1_CRITICAL,
    ),
    SLICategory.HALLUCINATION_GATE: ServiceLevelObjectiveConfig(
        sli_name=SLICategory.HALLUCINATION_GATE,
        display_name="Auditor Hallucination Gate (Principle I)",
        description="Zero unverified numeric claims permitted past Auditor Gate (100.0% verification).",
        target_percentage=1.000,
        target_threshold=0.0,
        unit="count",
        window_days=28,
        tier=SLOTier.TIER_1_CRITICAL,
    ),
}


def get_slo_config(sli_name: SLICategory | str) -> ServiceLevelObjectiveConfig:
    """Retrieves an SLO configuration by enum or string key."""
    if isinstance(sli_name, str):
        try:
            sli_name = SLICategory(sli_name)
        except ValueError:
            raise KeyError(f"Unknown SLI category: {sli_name}")
    return DEFAULT_SLO_CATALOG[sli_name]


def list_slo_configs() -> list[ServiceLevelObjectiveConfig]:
    """Returns a list of all configured production SLOs."""
    return list(DEFAULT_SLO_CATALOG.values())


def is_tier_1_critical(sli_name: SLICategory | str) -> bool:
    """Returns True if the SLO is governed under Tier 1 Critical release freeze rules."""
    config = get_slo_config(sli_name)
    return config.tier == SLOTier.TIER_1_CRITICAL
