"""Tests for Module B Naive Opposite Trade Baseline (T029)."""

from evals.suites.baselines.module_b_opposite import (
    NaiveOppositeTradeBaseline,
    evaluate_opposite_trades,
)


def test_naive_opposite_trade_matcher():
    trades = [
        {
            "trade_id": "TR1",
            "partner_id": "P1",
            "instrument": "EURUSD",
            "direction": "BUY",
            "timestamp": 100.0,
            "is_fraud": 1,
        },
        {
            "trade_id": "TR2",
            "partner_id": "P2",
            "instrument": "EURUSD",
            "direction": "SELL",
            "timestamp": 105.0,
            "is_fraud": 1,
        },
        {
            "trade_id": "TR3",
            "partner_id": "P3",
            "instrument": "GBPUSD",
            "direction": "BUY",
            "timestamp": 500.0,
            "is_fraud": 0,
        },
    ]
    baseline = NaiveOppositeTradeBaseline(time_window_seconds=10.0)
    flagged_pairs = baseline.find_opposite_pairs(trades)
    assert len(flagged_pairs) == 1
    assert flagged_pairs[0]["trade_a"] == "TR1"
    assert flagged_pairs[0]["trade_b"] == "TR2"


def test_naive_opposite_trade_metrics():
    trades = [
        {
            "trade_id": "TR1",
            "partner_id": "P1",
            "instrument": "EURUSD",
            "direction": "BUY",
            "timestamp": 100.0,
            "is_fraud": 1,
        },
        {
            "trade_id": "TR2",
            "partner_id": "P2",
            "instrument": "EURUSD",
            "direction": "SELL",
            "timestamp": 102.0,
            "is_fraud": 1,
        },
        {
            "trade_id": "TR3",
            "partner_id": "P3",
            "instrument": "USDJPY",
            "direction": "BUY",
            "timestamp": 200.0,
            "is_fraud": 0,
        },
    ]
    results = evaluate_opposite_trades(trades)
    assert "precision" in results
    assert "recall" in results
    assert "f1" in results
