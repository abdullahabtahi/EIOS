"""Pydantic v2 domain schemas for Closed-Loop Decision Learning Flywheel (014-flywheel)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MilestoneStatus(str, Enum):
    """Lifecycle status of a multi-horizon milestone outcome."""

    PENDING = "PENDING"
    RECORDED = "RECORDED"
    RECONCILED = "RECONCILED"


class DecisionOutcomeRecord(BaseModel):
    """Multi-horizon action decision record tracking proposal propensity score and 30d/60d/90d realized outcomes."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(..., description="Unique decision UUID")
    intent_id: str = Field(..., description="Referenced ActionIntentToken identifier")
    timestamp: datetime = Field(..., description="Decision proposal timestamp in UTC")
    service_name: str = Field(
        ..., description="Service proposing action, e.g. 'churn_service', 'aml_sentinel'"
    )
    action_type: str = Field(
        ..., description="Type of intervention proposed, e.g. 'fee_tier_restructure', 'step_up_kyc'"
    )
    entity_type: str = Field(..., description="Entity domain type, e.g. 'Partner', 'ClientAccount'")
    entity_id: str = Field(..., description="Target business entity ID")
    propensity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Proposing agent propensity score e(X) in [0, 1]"
    )
    treatment_assigned: bool = Field(
        ..., description="True if action approved and executed, False if control/rejected"
    )
    covariates: dict[str, Any] = Field(
        default_factory=dict, description="Observed pre-treatment context features X"
    )
    predicted_impact_30d: float = Field(..., description="Predicted quantitative impact at 30 days")
    actual_impact_30d: float | None = Field(
        None, description="Realized quantitative impact at 30 days"
    )
    residual_30d: float | None = Field(
        None, description="Forecast residual (actual - predicted) at 30 days"
    )
    status_30d: MilestoneStatus = Field(
        default=MilestoneStatus.PENDING, description="30-day milestone reconciliation state"
    )
    predicted_impact_60d: float = Field(..., description="Predicted quantitative impact at 60 days")
    actual_impact_60d: float | None = Field(
        None, description="Realized quantitative impact at 60 days"
    )
    residual_60d: float | None = Field(None, description="Forecast residual at 60 days")
    status_60d: MilestoneStatus = Field(
        default=MilestoneStatus.PENDING, description="60-day milestone reconciliation state"
    )
    predicted_impact_90d: float = Field(..., description="Predicted quantitative impact at 90 days")
    actual_impact_90d: float | None = Field(
        None, description="Realized quantitative impact at 90 days"
    )
    residual_90d: float | None = Field(None, description="Forecast residual at 90 days")
    status_90d: MilestoneStatus = Field(
        default=MilestoneStatus.PENDING, description="90-day milestone reconciliation state"
    )
    provenance_hash: str = Field(..., description="Cryptographic SHA-256 digest of record lineage")


class CausalUpliftEstimate(BaseModel):
    """Doubly Robust AIPW Average Treatment Effect estimate and Causal-Evidence Gate verification status."""

    model_config = ConfigDict(extra="forbid")

    estimate_id: str = Field(..., description="Unique estimate UUID")
    target_metric: str = Field(
        ..., description="Outcome metric evaluated, e.g. 'retained_revenue_60d'"
    )
    intervention_type: str = Field(..., description="Evaluated action type")
    sample_size: int = Field(..., ge=4, description="Total sample size evaluated")
    treatment_count: int = Field(..., ge=1, description="Number of treated units")
    control_count: int = Field(..., ge=1, description="Number of control units")
    ate_aipw: float = Field(
        ..., description="Doubly Robust AIPW estimated Average Treatment Effect"
    )
    standard_error: float = Field(
        ..., ge=0.0, description="Asymptotic influence-function standard error"
    )
    ci_lower: float = Field(..., description="95% confidence interval lower bound")
    ci_upper: float = Field(..., description="95% confidence interval upper bound")
    p_value: float = Field(..., ge=0.0, le=1.0, description="Two-sided p-value")
    is_significant: bool = Field(..., description="True if p-value < 0.05")
    causal_gate_passed: bool = Field(
        ..., description="True if passed Causal-Evidence Gate (Principle III)"
    )
    placebo_effect: float = Field(
        ..., description="Treatment effect under synthetic random placebo assignment"
    )
    refuter_stability_pct: float = Field(
        ..., ge=0.0, description="Effect stability percentage under random common cause addition"
    )
    evaluated_at: datetime = Field(..., description="Evaluation timestamp in UTC")


class SCMRecalibrationCheckpoint(BaseModel):
    """Immutable versioned snapshot of recalibrated Structural Causal Model DAG edge weights."""

    model_config = ConfigDict(extra="forbid")

    checkpoint_id: str = Field(..., description="Unique checkpoint UUID")
    version: str = Field(..., description="Semantic version of the SCM DAG")
    timestamp: datetime = Field(..., description="Checkpoint creation timestamp in UTC")
    edge_weights: dict[str, float] = Field(
        ..., description="Directed edge coefficients, e.g. 'driver->metric'"
    )
    baseline_residuals_mae: float = Field(
        ..., ge=0.0, description="Mean Absolute Error before recalibration"
    )
    recalibrated_residuals_mae: float = Field(
        ..., ge=0.0, description="Mean Absolute Error after recalibration"
    )
    is_acyclic: bool = Field(
        default=True, description="True if Kahn's topological sort confirms DAG acyclicity"
    )
    provenance_seed: str = Field(..., description="Reproducible evaluation dataset seed/hash")


class CalibrationDiagnosticsReport(BaseModel):
    """Model calibration health report summarizing Expected Calibration Error (ECE), Brier score, and drift flags."""

    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., description="Unique diagnostics report UUID")
    model_id: str = Field(..., description="Policy or predictive model ID")
    timestamp: datetime = Field(..., description="Diagnostic run timestamp in UTC")
    sample_count: int = Field(..., ge=0, description="Total predictions evaluated")
    expected_calibration_error: float = Field(
        ..., ge=0.0, le=1.0, description="Expected Calibration Error (ECE)"
    )
    brier_score: float = Field(..., ge=0.0, le=1.0, description="Brier score")
    reliability_bins: list[dict[str, Any]] = Field(
        default_factory=list, description="10-bin calibration distribution"
    )
    is_drift_detected: bool = Field(
        default=False, description="True if ECE > 0.15 indicates calibration drift"
    )


class PlaybookPolicyPrior(BaseModel):
    """Calibrated decision policy prior parameters governing frontline action recommendations."""

    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(..., description="Playbook policy identifier")
    action_type: str = Field(..., description="Intervention action type")
    empirical_win_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Observed success rate in outcomes ledger"
    )
    expected_payoff_usd: float = Field(
        ..., description="Expected net financial recovery or uplift in USD"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Calibrated decision confidence score"
    )
    sample_observations: int = Field(
        ..., ge=0, description="Count of historical decisions supporting this prior"
    )
    last_recalibrated_at: datetime = Field(..., description="Last recalibration timestamp in UTC")
