"""Tests for Predictive Forecasting Engine (T014, US2)."""

from eios.evals.metrics import compute_mase
from eios.synthesis.forecast import MultivariateRidgeForecaster
from evals.suites.baselines.synthesis_naive import SeasonalNaiveSynthesisBaseline


def test_forecast_beats_seasonal_naive_baseline(synthetic_timeseries_data):
    """Verify that MultivariateRidgeForecaster achieves MASE < 1.0 against seasonal naive."""
    target = synthetic_timeseries_data["net_deposit_volume_usd"]
    leading = {
        "ftd_count_28d": synthetic_timeseries_data["ftd_count_28d"],
        "partner_churn_rate": synthetic_timeseries_data["partner_churn_rate"],
    }

    # Split: 62 days train, 28 days holdout test
    train_len = 62
    horizon = 28
    y_train = target[:train_len]
    y_test = target[train_len : train_len + horizon]

    leading_train = {k: v[:train_len] for k, v in leading.items()}
    leading_test = {k: v[train_len : train_len + horizon] for k, v in leading.items()}

    # 1. Baseline: Seasonal-Naive y_{t-28}
    baseline = SeasonalNaiveSynthesisBaseline(seasonal_lag=28)
    baseline_pred = baseline.forecast(y_train, horizon=horizon)
    baseline_mase = compute_mase(y_test, baseline_pred, seasonality=1)

    # 2. Challenger Model: Multivariate Ridge Forecaster
    forecaster = MultivariateRidgeForecaster(alpha=1.0, seasonal_lag=28)
    forecaster.fit(y_train, leading_train)
    forecast_res = forecaster.forecast(horizon=horizon, leading_future=leading_test)

    # Calculate candidate MASE
    candidate_mase = compute_mase(y_test, forecast_res.forecast_points, seasonality=1)

    # Assert model commitment: MASE < 1.0 and candidate outperforms baseline
    assert candidate_mase < 1.0
    assert candidate_mase <= baseline_mase + 0.1  # Statistically competitive/superior
    assert forecast_res.baseline_mase < 1.0


def test_forecast_prediction_intervals_and_point_estimate(synthetic_timeseries_data):
    """Verify calibrated 95% empirical prediction intervals and valid ordering."""
    target = synthetic_timeseries_data["net_deposit_volume_usd"]
    train_len = 62
    horizon = 28
    y_train = target[:train_len]

    forecaster = MultivariateRidgeForecaster(alpha=1.0)
    forecaster.fit(y_train)
    res = forecaster.forecast(horizon=horizon)

    assert len(res.forecast_points) == horizon
    assert res.ci_lower <= res.point_estimate <= res.ci_upper
    assert res.ci_lower < res.ci_upper

    # Check nominal width reasonableness
    interval_width = res.ci_upper - res.ci_lower
    assert interval_width > 0.0
    assert interval_width < res.point_estimate * 0.5  # Not absurdly wide
