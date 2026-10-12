"""Contract validation tests for all 5 Closed-Loop Decision Learning Flywheel JSON Schemas."""

from datetime import UTC, datetime
import pytest
import jsonschema

from eios.flywheel.schemas import list_registered_schemas, load_schema, validate_contract
from eios.flywheel.models import (
    DecisionOutcomeRecord,
    CausalUpliftEstimate,
    SCMRecalibrationCheckpoint,
    CalibrationDiagnosticsReport,
    PlaybookPolicyPrior,
    MilestoneStatus,
)


def test_registered_schemas_count():
    schemas = list_registered_schemas()
    expected = [
        "calibration-diagnostics-report.schema.json",
        "causal-uplift-estimate.schema.json",
        "decision-outcome-record.schema.json",
        "playbook-policy-prior.schema.json",
        "scm-recalibration-checkpoint.schema.json",
    ]
    assert schemas == expected


def test_decision_outcome_record_contract():
    now = datetime.now(UTC)
    record = DecisionOutcomeRecord(
        decision_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        intent_id="INTENT-001",
        timestamp=now,
        service_name="churn_service",
        action_type="fee_tier_restructure",
        entity_type="Partner",
        entity_id="PARTNER-42",
        propensity_score=0.75,
        treatment_assigned=True,
        covariates={"score": 0.8},
        predicted_impact_30d=100.0,
        actual_impact_30d=110.0,
        residual_30d=10.0,
        status_30d=MilestoneStatus.RECONCILED,
        predicted_impact_60d=200.0,
        actual_impact_60d=None,
        residual_60d=None,
        status_60d=MilestoneStatus.PENDING,
        predicted_impact_90d=300.0,
        actual_impact_90d=None,
        residual_90d=None,
        status_90d=MilestoneStatus.PENDING,
        provenance_hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    )
    dumped = record.model_dump(mode="json")
    assert validate_contract(dumped, "decision-outcome-record") is True

    # Negative test: invalid propensity score > 1.0
    bad_dump = dict(dumped)
    bad_dump["propensity_score"] = 1.5
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(bad_dump, "decision-outcome-record")


def test_causal_uplift_estimate_contract():
    now = datetime.now(UTC)
    estimate = CausalUpliftEstimate(
        estimate_id="est-123",
        target_metric="retained_revenue_60d",
        intervention_type="fee_restructure",
        sample_size=100,
        treatment_count=50,
        control_count=50,
        ate_aipw=1250.0,
        standard_error=150.0,
        ci_lower=956.0,
        ci_upper=1544.0,
        p_value=0.0001,
        is_significant=True,
        causal_gate_passed=True,
        placebo_effect=12.5,
        refuter_stability_pct=95.2,
        evaluated_at=now,
    )
    dumped = estimate.model_dump(mode="json")
    assert validate_contract(dumped, "causal-uplift-estimate") is True

    # Negative test: sample_size < 4
    bad_dump = dict(dumped)
    bad_dump["sample_size"] = 2
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(bad_dump, "causal-uplift-estimate")


def test_scm_recalibration_checkpoint_contract():
    now = datetime.now(UTC)
    checkpoint = SCMRecalibrationCheckpoint(
        checkpoint_id="chk-001",
        version="v1.0.0",
        timestamp=now,
        edge_weights={"A->B": 0.5, "B->C": -1.2},
        baseline_residuals_mae=12.4,
        recalibrated_residuals_mae=8.1,
        is_acyclic=True,
        provenance_seed="seed-xyz",
    )
    dumped = checkpoint.model_dump(mode="json")
    assert validate_contract(dumped, "scm-recalibration-checkpoint") is True


def test_calibration_diagnostics_report_contract():
    now = datetime.now(UTC)
    report = CalibrationDiagnosticsReport(
        report_id="rep-001",
        model_id="churn-v1",
        timestamp=now,
        sample_count=200,
        expected_calibration_error=0.045,
        brier_score=0.12,
        reliability_bins=[{"bin": 1, "conf": 0.1, "acc": 0.12}],
        is_drift_detected=False,
    )
    dumped = report.model_dump(mode="json")
    assert validate_contract(dumped, "calibration-diagnostics-report") is True


def test_playbook_policy_prior_contract():
    now = datetime.now(UTC)
    prior = PlaybookPolicyPrior(
        policy_id="POL-01",
        action_type="fee_cut",
        empirical_win_rate=0.72,
        expected_payoff_usd=4500.0,
        confidence_score=0.85,
        sample_observations=150,
        last_recalibrated_at=now,
    )
    dumped = prior.model_dump(mode="json")
    assert validate_contract(dumped, "playbook-policy-prior") is True
