"""Core mathematical metrics and vectorized bootstrap confidence interval estimators (F04)."""

import math
from collections.abc import Sequence

import numpy as np

from eios.evals.models import MetricConfidenceInterval


def compute_pr_auc(y_true: Sequence[int], y_pred: Sequence[float]) -> float:
    """Compute Precision-Recall Area Under Curve (PR-AUC) using trapezoidal rule.

    Args:
        y_true: Ground-truth binary labels (0 or 1).
        y_pred: Predicted probabilities or continuous confidence scores.

    Returns:
        Scalar area under precision-recall curve in range [0.0, 1.0].
    """
    y_t = np.asarray(y_true, dtype=np.int32)
    y_p = np.asarray(y_pred, dtype=np.float64)

    total_positives = int(np.sum(y_t))
    if total_positives == 0 or len(y_t) == 0:
        return 0.0

    # Sort descending by prediction
    desc_indices = np.argsort(-y_p)
    y_t_sorted = y_t[desc_indices]

    tp = np.cumsum(y_t_sorted)
    fp = np.cumsum(1 - y_t_sorted)

    recalls = tp / total_positives
    precisions = tp / (tp + fp)

    # Prepend recall 0.0, precision 1.0
    recalls = np.concatenate(([0.0], recalls))
    precisions = np.concatenate(([1.0], precisions))

    # Support NumPy 2.0 np.trapezoid and legacy np.trapz
    trapz_fn = getattr(np, "trapezoid", getattr(np, "trapz", None))
    area = float(trapz_fn(precisions, recalls))
    return max(0.0, min(1.0, area))


def compute_brier_score(y_true: Sequence[int], y_pred: Sequence[float]) -> float:
    """Compute Brier calibration score (mean squared probability error).

    Args:
        y_true: Ground-truth binary labels (0 or 1).
        y_pred: Predicted probabilities in [0.0, 1.0].

    Returns:
        Scalar Brier score in range [0.0, 1.0] (0 = perfect calibration).
    """
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    if len(y_t) == 0:
        return 0.0
    return float(np.mean((y_t - y_p) ** 2))


def compute_mase(
    y_actual: Sequence[float],
    y_pred: Sequence[float],
    seasonality: int = 1,
) -> float:
    """Compute Mean Absolute Scaled Error (MASE) against a naive benchmark.

    Args:
        y_actual: Ground-truth continuous target sequence.
        y_pred: Model predicted sequence of identical length.
        seasonality: Seasonal period for naive benchmark differencing (default 1).

    Returns:
        Scalar MASE. Values < 1.0 indicate superiority over naive baseline.
    """
    y_a = np.asarray(y_actual, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)

    if len(y_a) == 0 or len(y_a) != len(y_p):
        return 0.0

    forecast_mae = np.mean(np.abs(y_a - y_p))

    if len(y_a) <= seasonality:
        return float(forecast_mae)

    naive_diff = np.abs(y_a[seasonality:] - y_a[:-seasonality])
    naive_mae = np.mean(naive_diff)

    if math.isclose(naive_mae, 0.0, abs_tol=1e-9):
        return float(forecast_mae)

    return float(forecast_mae / naive_mae)


def compute_lift(candidate: float, baseline: float) -> tuple[float, float]:
    """Compute absolute and relative performance lift of candidate over baseline.

    Args:
        candidate: Candidate model metric score.
        baseline: Naive baseline metric score.

    Returns:
        Tuple of (absolute_delta, relative_lift_pct).
    """
    absolute_delta = candidate - baseline
    if math.isclose(baseline, 0.0, abs_tol=1e-9):
        relative_lift_pct = 0.0 if math.isclose(candidate, 0.0, abs_tol=1e-9) else 100.0
    else:
        relative_lift_pct = (absolute_delta / baseline) * 100.0
    return absolute_delta, relative_lift_pct


def bootstrap_confidence_interval(
    data: Sequence[float],
    confidence_level: float = 0.95,
    n_resamples: int = 1000,
    seed: int | None = 42,
) -> MetricConfidenceInterval:
    """Compute bootstrap percentile confidence interval using vectorized 2D NumPy array.

    Args:
        data: Sample values (e.g. metric scores across validation seeds).
        confidence_level: Desired coverage probability (default 0.95).
        n_resamples: Number of bootstrap replicas B (default 1000).
        seed: Random seed for reproducible resampling.

    Returns:
        MetricConfidenceInterval instance containing lower, median, upper bounds.
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

    rng = np.random.default_rng(seed)
    # Vectorized 2D indexing for speed (< 3s on 10,000 samples)
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
