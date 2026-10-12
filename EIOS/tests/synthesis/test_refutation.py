"""Unit tests for DoWhy-style causal refutation engine (T008, US1)."""

from eios.synthesis.refutation import (
    run_data_subset_refuter,
    run_edge_refutation_suite,
    run_placebo_treatment_refuter,
    run_random_common_cause_refuter,
)


def test_placebo_treatment_refuter_passes_on_true_causal_edge(synthetic_timeseries_data):
    """Permuting true treatment should yield effect near 0, giving p > 0.05 (PASS)."""
    treatment = synthetic_timeseries_data["competitor_payout_rate"]
    outcome = synthetic_timeseries_data["partner_churn_rate"]

    res = run_placebo_treatment_refuter(treatment, outcome, n_permutations=100)
    assert res["p_value"] > 0.05
    assert res["passed"] is True
    assert abs(res["placebo_effect_mean"]) < 0.1


def test_random_common_cause_refuter_stability(synthetic_timeseries_data):
    """Adding random confounder should keep effect estimate stable within 20%."""
    treatment = synthetic_timeseries_data["competitor_payout_rate"]
    outcome = synthetic_timeseries_data["partner_churn_rate"]

    res = run_random_common_cause_refuter(treatment, outcome)
    assert res["passed"] is True
    assert res["delta_pct"] <= 0.20


def test_data_subset_refuter_stability(synthetic_timeseries_data):
    """Subsetting data to 80% slices should keep effect estimate stable within 20%."""
    treatment = synthetic_timeseries_data["competitor_payout_rate"]
    outcome = synthetic_timeseries_data["partner_churn_rate"]

    res = run_data_subset_refuter(treatment, outcome, subset_fraction=0.8, n_subsets=30)
    assert res["passed"] is True
    assert res["relative_std"] <= 0.20


def test_full_refutation_suite_and_placebo_rejection(synthetic_timeseries_data):
    """Full suite passes true causal edge and rejects planted placebo edge."""
    # 1. True Causal Edge: competitor_payout -> partner_churn
    true_edge_report = run_edge_refutation_suite(
        edge_id="competitor_payout_rate->partner_churn_rate",
        treatment=synthetic_timeseries_data["competitor_payout_rate"],
        outcome=synthetic_timeseries_data["partner_churn_rate"],
        is_placebo=False,
    )
    assert true_edge_report.gate_verdict == "PASS"
    assert true_edge_report.ci_excludes_zero is True
    assert true_edge_report.placebo_p_value > 0.05

    # 2. Planted Placebo Edge: avg_spread_pip -> partner_churn_rate (true effect = 0)
    placebo_report = run_edge_refutation_suite(
        edge_id="avg_spread_pip->partner_churn_rate",
        treatment=synthetic_timeseries_data["avg_spread_pip"],
        outcome=synthetic_timeseries_data["partner_churn_rate"],
        is_placebo=True,
    )
    assert placebo_report.gate_verdict == "FAIL"
    assert "Placebo edge failed causal gate" in (placebo_report.failure_reason or "")
