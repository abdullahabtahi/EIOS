"""Tests for Module C Recency Churn Baseline (T030)."""

from evals.suites.baselines.module_c_recency import (
    RecencyChurnBaseline,
    evaluate_recency_churn,
)


def test_recency_churn_baseline():
    partners = [
        {"partner_id": "P1", "days_since_last_login": 35, "churned_30d": 1, "actual_churn_day": 40},
        {
            "partner_id": "P2",
            "days_since_last_login": 2,
            "churned_30d": 0,
            "actual_churn_day": None,
        },
        {"partner_id": "P3", "days_since_last_login": 20, "churned_30d": 1, "actual_churn_day": 25},
    ]
    baseline = RecencyChurnBaseline(inactivity_threshold_days=14)
    scores = baseline.predict_proba(partners)
    assert scores[0] >= 0.8
    assert scores[1] <= 0.2
    assert scores[2] >= 0.6


def test_recency_churn_lead_time_metrics():
    partners = [
        {"partner_id": "P1", "days_since_last_login": 35, "churned_30d": 1, "actual_churn_day": 40},
        {
            "partner_id": "P2",
            "days_since_last_login": 2,
            "churned_30d": 0,
            "actual_churn_day": None,
        },
        {"partner_id": "P3", "days_since_last_login": 20, "churned_30d": 1, "actual_churn_day": 25},
    ]
    res = evaluate_recency_churn(partners)
    assert "pr_auc" in res
    assert "median_lead_time_days" in res
    assert res["median_lead_time_days"] >= 0.0
