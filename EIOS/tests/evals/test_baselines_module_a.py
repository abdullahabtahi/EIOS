"""Tests for Module A Static Rule Baseline (T028)."""

from evals.suites.baselines.module_a_rules import (
    RuleBasedAMLBaseline,
    score_aml_transactions,
)


def test_rule_based_aml_baseline_scoring():
    transactions = [
        {"tx_id": "T1", "amount": 12000.0, "velocity_1h": 6, "is_sar": 1},
        {"tx_id": "T2", "amount": 200.0, "velocity_1h": 1, "is_sar": 0},
        {"tx_id": "T3", "amount": 15000.0, "velocity_1h": 10, "is_sar": 1},
        {"tx_id": "T4", "amount": 9500.0, "velocity_1h": 2, "is_sar": 0},
    ]
    baseline = RuleBasedAMLBaseline(amount_threshold=10000.0, velocity_threshold=5)
    scores = baseline.predict_proba(transactions)
    assert len(scores) == 4
    # T1 and T3 trigger both rules -> high risk score
    assert scores[0] >= 0.8
    assert scores[1] <= 0.2
    assert scores[2] >= 0.8
    assert scores[3] <= 0.5


def test_rule_based_aml_metrics():
    transactions = [
        {"tx_id": "T1", "amount": 15000.0, "velocity_1h": 7, "is_sar": 1},
        {"tx_id": "T2", "amount": 300.0, "velocity_1h": 1, "is_sar": 0},
        {"tx_id": "T3", "amount": 12000.0, "velocity_1h": 8, "is_sar": 1},
        {"tx_id": "T4", "amount": 500.0, "velocity_1h": 1, "is_sar": 0},
    ]
    results = score_aml_transactions(transactions)
    assert "pr_auc" in results
    assert "brier_score" in results
    assert "fpr" in results
    assert 0.0 <= results["fpr"] <= 1.0
