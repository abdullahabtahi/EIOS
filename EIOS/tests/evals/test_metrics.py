"""Test mathematical metric utilities and bootstrap confidence intervals (T006)."""

import pytest

from eios.evals.metrics import (
    bootstrap_confidence_interval,
    compute_brier_score,
    compute_lift,
    compute_mase,
    compute_pr_auc,
)


def test_compute_pr_auc(sample_predictions: tuple[list[float], list[int]]):
    y_pred, y_true = sample_predictions
    score = compute_pr_auc(y_true, y_pred)
    assert 0.80 <= score <= 1.0


def test_compute_brier_score(sample_predictions: tuple[list[float], list[int]]):
    y_pred, y_true = sample_predictions
    brier = compute_brier_score(y_true, y_pred)
    assert 0.0 <= brier <= 0.15  # Good calibration should be close to 0


def test_compute_mase(sample_time_series: tuple[list[float], list[float]]):
    y_actual, y_pred = sample_time_series
    mase = compute_mase(y_actual, y_pred)
    assert 0.0 < mase < 1.0  # Beats naive baseline


def test_compute_lift():
    lift_abs, lift_rel = compute_lift(candidate=0.85, baseline=0.70)
    assert pytest.approx(lift_abs, rel=1e-3) == 0.15
    assert pytest.approx(lift_rel, rel=1e-3) == 21.4285


def test_bootstrap_confidence_interval():
    data = [0.75, 0.78, 0.80, 0.82, 0.79, 0.81, 0.83, 0.77, 0.80, 0.82]
    ci = bootstrap_confidence_interval(data, confidence_level=0.95, n_resamples=500)
    assert ci.lower < ci.median < ci.upper
    assert 0.75 <= ci.lower <= 0.79
    assert 0.80 <= ci.upper <= 0.85
