"""Causal covariate matrix builder and propensity score clipping utilities."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple
import numpy as np

from eios.flywheel.models import DecisionOutcomeRecord


DEFAULT_PROPENSITY_EPSILON = 0.01


def clip_propensity_scores(
    propensities: np.ndarray | Sequence[float],
    epsilon: float = DEFAULT_PROPENSITY_EPSILON,
) -> np.ndarray:
    """Clips propensity scores to [epsilon, 1 - epsilon] to avoid unbounded IPW variance.

    As documented in Imbens & Rubin (2015), extreme propensity scores near 0 or 1
    yield extreme variance in inverse propensity weights. Clipping to [0.01, 0.99]
    preserves numerical stability and prevents outlier disruption.
    """
    arr = np.asarray(propensities, dtype=np.float64)
    lower = max(0.0, float(epsilon))
    upper = min(1.0, 1.0 - float(epsilon))
    return np.clip(arr, lower, upper)


class CovariateMatrixBuilder:
    """Extracts, standardizes, and aligns covariate matrices from DecisionOutcomeRecords."""

    def __init__(self, feature_names: Sequence[str] | None = None) -> None:
        self.feature_names = list(feature_names) if feature_names is not None else None

    def fit_feature_names(self, records: Sequence[DecisionOutcomeRecord]) -> List[str]:
        """Discovers sorted distinct numerical feature keys across records."""
        names: set[str] = set()
        for r in records:
            if r.covariates:
                for k, v in r.covariates.items():
                    if isinstance(v, (int, float, bool)):
                        names.add(k)
        self.feature_names = sorted(list(names)) if names else ["constant"]
        return self.feature_names

    def build_matrix(
        self,
        records: Sequence[DecisionOutcomeRecord],
    ) -> np.ndarray:
        """Constructs an (N, K) float64 covariate matrix from records."""
        if not records:
            return np.empty((0, 0), dtype=np.float64)

        if self.feature_names is None:
            self.fit_feature_names(records)

        feat_names = self.feature_names or ["constant"]
        n_samples = len(records)
        n_features = len(feat_names)
        matrix = np.zeros((n_samples, n_features), dtype=np.float64)

        for i, r in enumerate(records):
            for j, f in enumerate(feat_names):
                if f == "constant":
                    matrix[i, j] = 1.0
                elif r.covariates and f in r.covariates:
                    val = r.covariates[f]
                    try:
                        matrix[i, j] = float(val)
                    except (ValueError, TypeError):
                        matrix[i, j] = 0.0
                else:
                    matrix[i, j] = 0.0

        return matrix

    def extract_aligned_arrays(
        self,
        records: Sequence[DecisionOutcomeRecord],
        target_horizon: str = "30d",
        epsilon: float = DEFAULT_PROPENSITY_EPSILON,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
        """Extracts aligned (Y, W, e, X, valid_ids) for causal estimation.

        Returns:
            Y: Outcome array (actual impact for target_horizon)
            W: Treatment array (0 or 1)
            e: Clipped propensity scores array
            X: Covariate matrix
            record_ids: IDs of included records with non-null actuals
        """
        valid_records: List[DecisionOutcomeRecord] = []
        outcomes: List[float] = []

        for r in records:
            actual: float | None = None
            if target_horizon == "30d":
                actual = r.actual_impact_30d
            elif target_horizon == "60d":
                actual = r.actual_impact_60d
            elif target_horizon == "90d":
                actual = r.actual_impact_90d
            else:
                raise ValueError(f"Unsupported target horizon: {target_horizon}")

            if actual is not None:
                valid_records.append(r)
                outcomes.append(float(actual))

        if not valid_records:
            return (
                np.empty((0,), dtype=np.float64),
                np.empty((0,), dtype=np.float64),
                np.empty((0,), dtype=np.float64),
                np.empty((0, 0), dtype=np.float64),
                [],
            )

        Y = np.asarray(outcomes, dtype=np.float64)
        W = np.asarray([1.0 if r.treatment_assigned else 0.0 for r in valid_records], dtype=np.float64)
        raw_e = np.asarray([r.propensity_score for r in valid_records], dtype=np.float64)
        e = clip_propensity_scores(raw_e, epsilon=epsilon)
        X = self.build_matrix(valid_records)
        record_ids = [r.decision_id for r in valid_records]

        return Y, W, e, X, record_ids
