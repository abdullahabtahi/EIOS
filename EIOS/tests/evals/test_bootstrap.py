"""Tests for Vectorized Bootstrap Confidence Interval Estimator (T039)."""

import time

import numpy as np

from evals.suites.splits.bootstrap import compute_vectorized_bootstrap_ci


def test_bootstrap_runtime_and_bounds():
    # 10,000 samples from normal distribution N(0.80, 0.05^2)
    rng = np.random.default_rng(42)
    data = rng.normal(loc=0.80, scale=0.05, size=10000)

    start = time.perf_counter()
    ci = compute_vectorized_bootstrap_ci(data, confidence_level=0.95, n_resamples=1000)
    elapsed = time.perf_counter() - start

    # Performance constraint: runtime < 3s per 10,000 samples
    assert elapsed < 3.0

    # Theoretical standard error of mean = 0.05 / sqrt(10000) = 0.0005
    # Mean is tightly bounded around 0.80 +/- 0.001
    assert 0.798 <= ci.median <= 0.802
    assert 0.797 <= ci.lower <= 0.801
    assert 0.799 <= ci.upper <= 0.803
    assert ci.lower < ci.median < ci.upper


def test_bootstrap_empty_and_single_sample():
    ci_empty = compute_vectorized_bootstrap_ci([])
    assert ci_empty.lower == 0.0
    assert ci_empty.upper == 0.0

    ci_single = compute_vectorized_bootstrap_ci([0.75])
    assert ci_single.lower == 0.75
    assert ci_single.upper == 0.75
