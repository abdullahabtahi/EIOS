"""Vectorized Bootstrap Confidence Interval Calculator (T042).

Uses 2D NumPy array matrix indexing to calculate percentile bootstrap confidence intervals
in < 3 seconds across 10,000 samples.
"""

from collections.abc import Sequence

import numpy as np

from eios.evals.models import MetricConfidenceInterval


def compute_vectorized_bootstrap_ci(
    data: Sequence[float] | np.ndarray,
    confidence_level: float = 0.95,
    n_resamples: int = 1000,
    seed: int | None = 42,
) -> MetricConfidenceInterval:
    """Compute bootstrap percentile confidence interval using vectorized 2D NumPy array operations.

    Args:
        data: Sample observations.
        confidence_level: Desired coverage probability (default 0.95).
        n_resamples: Number of bootstrap iterations B (default 1000).
        seed: Random seed for reproducibility.

    Returns:
        MetricConfidenceInterval with lower, median, upper bounds.
    """
    arr = np.asarray(data, dtype=np.float64)
    n = len(arr)
    if n == 0:
        return MetricConfidenceInterval(
            lower=0.0,
            median=0.0,
            upper=0.0,
            confidence_level=confidence_level,
        )
    if n == 1:
        val = float(arr[0])
        return MetricConfidenceInterval(
            lower=val,
            median=val,
            upper=val,
            confidence_level=confidence_level,
        )

    rng = np.random.default_rng(seed)
    # 2D indexing for speed (< 3s on 10,000 elements with B=1,000)
    idx = rng.integers(0, n, size=(n_resamples, n))
    boot_means = np.mean(arr[idx], axis=1)

    alpha = (1.0 - confidence_level) / 2.0
    lower_pct = alpha * 100.0
    upper_pct = (1.0 - alpha) * 100.0

    lower = float(np.percentile(boot_means, lower_pct))
    median = float(np.percentile(boot_means, 50.0))
    upper = float(np.percentile(boot_means, upper_pct))

    return MetricConfidenceInterval(
        lower=lower,
        median=median,
        upper=upper,
        confidence_level=confidence_level,
    )
