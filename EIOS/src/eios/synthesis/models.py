"""Pydantic v2 domain models for Executive Synthesis Engine (F05)."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CausalEdge(BaseModel):
    """Directed causal link between two business metrics in the SCM DAG."""

    source_metric: str
    target_metric: str
    weight: float
    ci_lower: float
    ci_upper: float
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    is_placebo: bool = False

    @property
    def from_metric(self) -> str:
        return self.source_metric

    @property
    def to_metric(self) -> str:
        return self.target_metric

    def to_omcp_dict(self) -> dict[str, Any]:
        """Convert to canonical OMCP dictionary format."""
        return {
            "from": self.source_metric,
            "to": self.target_metric,
            "weight": self.weight,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "is_placebo": self.is_placebo,
        }


class RefutationReport(BaseModel):
    """Empirical refutation metrics certifying causal validity under Causal-Evidence Gate."""

    edge_id: str
    placebo_p_value: float
    placebo_effect: float = 0.0  # the permuted-treatment effect the p-value tests against zero
    random_cause_delta_pct: float
    subset_stability_delta_pct: float
    ci_excludes_zero: bool
    gate_verdict: str  # "PASS" | "FAIL" | "UNVERIFIED"
    failure_reason: str | None = None


class SCMCacheManifest(BaseModel):
    """Serialized manifest of certified SCM DAG edges, weights, and refutation reports."""

    model_version: str
    generated_at: datetime
    git_sha: str
    dataset_hash: str
    edges: list[CausalEdge]
    refutations: dict[str, RefutationReport]
    active_edge_count: int
    rejected_placebo_count: int


class DriverAttribution(BaseModel):
    """Constituent driver metric contribution strictly summing to 100.0%."""

    driver_metric: str
    absolute_impact: float
    percentage: float = Field(ge=0.0, le=100.0)
    direction: str  # "POSITIVE" | "NEGATIVE"


class ForecastResult(BaseModel):
    """Predictive time-series forecast with prediction intervals and driver attribution."""

    metric_id: str
    horizon_days: int = Field(ge=1)
    historical_points: list[float]
    forecast_points: list[float]
    point_estimate: float
    ci_lower: float
    ci_upper: float
    baseline_mase: float
    driver_attributions: list[DriverAttribution]
    total_attribution_percentage: float = 100.0

    @field_validator("total_attribution_percentage")
    @classmethod
    def validate_sum_100(cls, v: float) -> float:
        if abs(v - 100.0) > 0.01:
            raise ValueError(f"Driver attribution total must equal 100.0%, got {v:.4f}%")
        return v


class ScenarioShockSpec(BaseModel):
    """Exogenous shock parameters applied to the structural causal graph."""

    scenario_name: str
    shocks: dict[str, float]
    duration_days: int = 28
    assumptions: list[str] = Field(default_factory=list)


class MitigationOption(BaseModel):
    """Ranked strategic defensive action responding to simulated scenario impact."""

    action_type: str
    target_cohort: str
    estimated_cost_usd: float
    estimated_revenue_recovered_usd: float
    roi_ratio: float
    confidence: float = Field(ge=0.0, le=1.0)


class ScenarioSimulationResult(BaseModel):
    """Propagated downstream impacts, confidence bounds, and ranked mitigations."""

    scenario_name: str
    propagated_deltas: dict[str, float]
    confidence_intervals: dict[str, tuple[float, float]]
    mitigation_options: list[MitigationOption]
    assumptions_applied: list[str]
    execution_time_ms: float


class BriefingItem(BaseModel):
    """Structured insight, risk, or opportunity surfaced in the morning briefing."""

    item_id: str
    category: str  # "INSIGHT" | "RISK" | "OPPORTUNITY"
    title: str
    summary: str
    severity_or_impact: str  # "HIGH" | "MEDIUM" | "LOW"
    metric_citations: list[str]
    follow_up_prompt: str


class BriefingObject(BaseModel):
    """Complete daily morning executive briefing."""

    briefing_id: str
    briefing_date: str
    generated_at: datetime
    insights: list[BriefingItem]
    risks: list[BriefingItem]
    opportunities: list[BriefingItem]
    is_cached_replay: bool = False
    provenance_tag: str = "[TARGET]"


class RecommendationCard(BaseModel):
    """Human-in-the-loop decision card proposing a governed action."""

    recommendation_id: str
    action_type: str
    target_entity_id: str
    impact_estimate_min: float
    impact_estimate_max: float
    impact_unit: str  # "USD" | "BPS" | "RATIO"
    pros: list[str]
    cons: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_citations: list[str]
    propensity_score: float = Field(ge=0.01, le=0.99)
    causal_context: dict[str, float]


class AIPWPropensityRecord(BaseModel):
    """Logged decision intent for offline causal flywheel recalibration."""

    intent_id: str
    action_type: str
    target_entity_id: str
    propensity_score: float = Field(ge=0.01, le=0.99)
    covariates: dict[str, float]
    action_taken: int = Field(ge=0, le=1)
    observed_outcome: float | None = None
    logged_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
