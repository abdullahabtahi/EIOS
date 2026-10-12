"""Tests for Synthesis Baseline: Seasonal Naive & Equal Attribution (T031)."""

from evals.suites.baselines.synthesis_naive import (
    SeasonalNaiveSynthesisBaseline,
    evaluate_synthesis_baseline,
)


def test_seasonal_naive_forecast():
    # 35 days of history
    history = [float(100 + (i % 7) * 5) for i in range(35)]
    baseline = SeasonalNaiveSynthesisBaseline(seasonal_lag=28)
    forecast = baseline.forecast(history, horizon=7)
    assert len(forecast) == 7
    # For day 35 (horizon 0), forecast matches day 35-28 = day 7
    assert forecast[0] == history[7]


def test_equal_split_driver_attribution():
    drivers = ["competitive_entry", "partner_disengagement", "macro_volatility"]
    baseline = SeasonalNaiveSynthesisBaseline()
    attribution = baseline.attribute_drivers(drivers)
    assert len(attribution) == 3
    total_pct = sum(attribution.values())
    assert abs(total_pct - 100.0) < 1e-4
    for val in attribution.values():
        assert abs(val - 33.3333) < 0.01


def test_evaluate_synthesis_baseline():
    actual = [100.0, 105.0, 110.0, 108.0]
    predicted = [99.0, 104.0, 109.0, 107.0]
    res = evaluate_synthesis_baseline(actual, predicted)
    assert "mase" in res
    assert res["attribution_equal_split_sum"] == 100.0
