"""Pydantic v2 domain schemas for Client Fraud Sentinel / AML Transaction Monitoring.

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/data-model.md
- .specify/memory/constitution.md (Principles I, II, IV, VII)
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AMLTriggerType(str, Enum):
    """Surveillance trigger typology."""

    THRESHOLD_RULE = "THRESHOLD_RULE"
    ROUND_TRIP_SEQUENCE = "ROUND_TRIP_SEQUENCE"
    MULE_RING_CLUSTER = "MULE_RING_CLUSTER"
    COHORT_DEVIATION = "COHORT_DEVIATION"
    SUPERVISED_TRIAGE = "SUPERVISED_TRIAGE"


class AMLPriorityTier(str, Enum):
    """Investigation priority tier."""

    CRITICAL = "CRITICAL"  # Top 50 prioritized case
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AMLTypology(str, Enum):
    """Categorized financial crime typology."""

    STRUCTURING = "STRUCTURING"
    MICRO_PNL_WASH = "MICRO_PNL_WASH"
    MULE_SYNDICATE = "MULE_SYNDICATE"
    RAPID_MOVEMENT = "RAPID_MOVEMENT"
    NONE = "NONE"


class WithdrawalDisposition(str, Enum):
    """Action recommendation for real-time pre-withdrawal evaluation."""

    ALLOW = "ALLOW"
    PROPOSE_HOLD = "PROPOSE_HOLD"
    PROPOSE_FREEZE = "PROPOSE_FREEZE"


class AMLAlert(BaseModel):
    """Core transaction surveillance alert."""

    model_config = ConfigDict(strict=True, frozen=True)

    alert_id: str
    client_id: str
    trigger_type: AMLTriggerType
    risk_score: float = Field(ge=0.0, le=1.0)
    priority_tier: AMLPriorityTier
    typology: AMLTypology
    amount_usd: float = Field(ge=0.0)
    triggered_at: datetime
    is_triage_top50: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class RoundTripTypology(BaseModel):
    """Structured wash/layering pattern (deposit -> micro-trade -> withdrawal within 72h KYC)."""

    model_config = ConfigDict(strict=True, frozen=True)

    event_id: str
    client_id: str
    deposit_txn_id: str
    withdrawal_txn_id: str
    deposit_amount_usd: float = Field(ge=0.0)
    withdrawal_amount_usd: float = Field(ge=0.0)
    trade_count: int = Field(ge=0)
    net_pl_usd: float
    market_risk_pct: float = Field(ge=0.0)
    holding_duration_seconds: float = Field(ge=0.0)
    hours_since_kyc: float = Field(ge=0.0)
    typology_risk_score: float = Field(ge=0.0, le=1.0)


class MuleRingCluster(BaseModel):
    """Graph cluster of accounts linked by shared tokens with hub suppression."""

    model_config = ConfigDict(strict=True, frozen=True)

    cluster_id: str
    member_client_ids: list[str]
    shared_payment_tokens: list[str]
    shared_device_tokens: list[str]
    shared_ip_tokens: list[str]
    suppressed_hub_tokens: list[str]
    cluster_size: int = Field(ge=1)
    total_volume_usd: float = Field(ge=0.0)
    is_syndicate: bool
    plain_language_explanation: str


class WithdrawalRiskAssessment(BaseModel):
    """Real-time pre-withdrawal risk evaluation result."""

    model_config = ConfigDict(strict=True, frozen=True)

    assessment_id: str
    withdrawal_id: str
    client_id: str
    amount_usd: float = Field(ge=0.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    recommendation: WithdrawalDisposition
    decision_latency_ms: float = Field(ge=0.0)
    intent_id: str | None = None
    evaluated_at: datetime


class SARDraft(BaseModel):
    """Regulator-ready Suspicious Activity Report (FinCEN / FIU standard format)."""

    model_config = ConfigDict(strict=True, frozen=True)

    sar_id: str
    case_id: str
    client_id: str
    jurisdiction: str
    filing_type: str
    subject_info: dict[str, Any]
    suspicious_activity_summary: str
    chronological_transactions: list[dict[str, Any]]
    narrative_basis: str
    statutory_provisions: list[str]
    evidence_citations: list[str]
    created_at: datetime
    is_replay_fallback: bool = False


class AMLCaseDossier(BaseModel):
    """Unified AML investigation pack aggregating 5+ source systems."""

    model_config = ConfigDict(strict=True, frozen=True)

    case_id: str
    client_id: str
    as_of: datetime
    kyc_tier: str
    kyc_approved_at: datetime | None
    total_deposit_usd: float = Field(ge=0.0)
    total_withdrawal_usd: float = Field(ge=0.0)
    net_trading_pl_usd: float
    deposit_withdrawal_ratio: float = Field(ge=0.0)
    roundtrip_events: list[RoundTripTypology]
    mule_ring_id: str | None
    mule_ring_size: int = 0
    composite_risk_score: float = Field(ge=0.0, le=1.0)
    priority_tier: AMLPriorityTier
    recommended_action: str
    citations: list[str]
    statutory_references: list[str]
    narrative_summary: str
    sar_draft: SARDraft | None = None
