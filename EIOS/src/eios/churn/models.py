"""Domain models and Pydantic v2 schemas for Partner Churn Radar (T002)."""

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


class SignalFamily(StrEnum):
    BEHAVIORAL = "BEHAVIORAL"
    COMMUNICATION = "COMMUNICATION"
    RELATIONSHIP = "RELATIONSHIP"
    FINANCIAL = "FINANCIAL"
    COMPETITIVE = "COMPETITIVE"


class RiskTier(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class InterventionWindow(StrEnum):
    OPTIMAL = "OPTIMAL"
    LATE_STAGE = "LATE_STAGE"
    EARLY_WATCH = "EARLY_WATCH"
    STABLE = "STABLE"


class SignalContribution(BaseModel):
    """Deterministic contribution of an individual signal family feature."""
    signal_family: SignalFamily
    metric_name: str
    observed_value: float
    baseline_value: float
    relative_delta: float
    hazard_weight: float = 0.0
    citation_ref: str = Field(..., description="Canonical L1 Data Product citation (e.g. DP9:partner_engagement_signals)")


class ChurnExplanationRecord(BaseModel):
    """Audited plain-language root-cause narrative synthesized from tool outputs."""
    explanation_id: str
    partner_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    narrative: str
    citations: list[str] = Field(default_factory=list)
    is_replay: bool = False


class HazardScore(BaseModel):
    """Calibrated 30-day hazard score and priority rating for a partner."""
    partner_id: str
    as_of_date: date
    hazard_probability_30d: float = Field(..., ge=0.0, le=1.0)
    priority_score: float = Field(..., ge=0.0, description="hazard_probability_30d * value_at_risk_usd")
    risk_tier: RiskTier
    intervention_window: InterventionWindow
    change_point_flag: bool = False
    top_driver_family: SignalFamily = SignalFamily.BEHAVIORAL
    top_driver_metric: str = "login_velocity_decay_3w"
    top_driver_delta: float = 0.0
    top_contributing_signals: list[SignalContribution] = Field(default_factory=list)
    explanation: ChurnExplanationRecord | None = None


class CohortAnomalyAlert(BaseModel):
    """Systemic regional or segment disengagement cluster alert."""
    alert_id: str = ""
    cohort_id: str = ""
    region_id: str
    partner_count: int = Field(..., ge=1)
    affected_partner_ids: list[str] = Field(default_factory=list)
    aggregate_value_at_risk_usd: float = Field(..., ge=0.0)
    p_value: float = Field(..., ge=0.0, le=1.0, description="Statistical significance under permutation test")
    common_driver: str
    recommended_playbook: str = "LaunchRegionalAffiliateIncentive"
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["ACTIVE", "ACKNOWLEDGED", "RESOLVED"] = "ACTIVE"

    @model_validator(mode="after")
    def sync_ids(self) -> "CohortAnomalyAlert":
        if not self.cohort_id and self.alert_id:
            self.cohort_id = self.alert_id
        elif not self.alert_id and self.cohort_id:
            self.alert_id = self.cohort_id
        return self


class ActionIntentProposal(BaseModel):
    """Retention Playbook Action Intent proposal payload."""
    partner_ids: list[str] = Field(..., min_length=1)
    playbook_id: str
    budget: float = Field(..., ge=0.0)
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
    propensity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    causal_context: dict[str, Any] = Field(default_factory=dict)


class DecisionOutcomeRecord(BaseModel):
    """Forward outcome record used for Doubly Robust AIPW causal estimation."""
    outcome_id: str
    intent_id: str
    partner_id: str
    playbook_id: str
    treatment_assigned: int = Field(..., ge=0, le=1, description="1 if treated, 0 if control")
    propensity_score: float = Field(..., ge=0.0, le=1.0)
    observed_retained_revenue_60d: float
    actual_churn_60d: bool
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    manager_override_flag: bool = Field(default=False, description="Flag indicating human manager intervened/overrode default recommendation")
    override_reason: str | None = Field(default=None, description="Qualitative justification for override")
    unobserved_signal_proxy: float = Field(default=0.0, description="Quantitative proxy score for unobserved confounders")


class DisengagementTheme(BaseModel):
    """Structured hypothesis of an emerging churn pattern discovered in tickets."""
    theme_id: str
    title: str = Field(..., description="Concise theme title (e.g. MT5 WebSocket Rate Limit Frustration)")
    affected_partner_count: int = Field(..., ge=1)
    signal_families_implicated: list[SignalFamily] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    supporting_ticket_ids: list[str] = Field(default_factory=list)
    plain_language_summary: str
    actionable_remediation: str


class PartnerSignalsResponse(BaseModel):
    """Canonical OMCP tool response schema for get_partner_signals."""
    partner_id: str
    tier: Literal["TIER_1", "TIER_2", "TIER_3", "VIP_MASTER"]
    region_id: str
    value_at_risk_usd: float
    hazard_probability_30d: float
    priority_score: float
    risk_tier: RiskTier
    intervention_window: InterventionWindow
    change_point_detected: bool
    top_contributing_signals: list[SignalContribution]
    explanation: ChurnExplanationRecord


class CohortAlertsResponse(BaseModel):
    """Canonical OMCP tool response schema for get_high_risk_cohorts."""
    cohorts: list[CohortAnomalyAlert] = Field(default_factory=list)
