"""QuantumBlack Model Drift Surveillance Engine (F019 Phase 8, T026).

Calculates Population Stability Index (PSI) and Brier calibration scores over sliding windows
to detect feature distribution shifts and model degradation before downstream decision corruption.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import numpy as np
from pydantic import BaseModel, Field


class DriftAlertSeverity(str):
    STABLE = "STABLE"
    MODERATE_SHIFT = "MODERATE_SHIFT"
    SIGNIFICANT_DRIFT = "SIGNIFICANT_DRIFT"


class PSICalculationResult(BaseModel):
    feature_name: str
    psi_score: float
    severity: str
    bin_counts_expected: list[int]
    bin_counts_actual: list[int]
    is_drift_detected: bool
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DriftSurveillanceEngine:
    """Surveillance engine for continuous model monitoring in compliance with McKinsey / QuantumBlack protocols."""

    PSI_STABLE_THRESHOLD = 0.10
    PSI_DRIFT_THRESHOLD = 0.25

    def calculate_psi(
        self,
        expected_distribution: Sequence[float],
        actual_distribution: Sequence[float],
        feature_name: str = "partner_churn_hazard",
        num_bins: int = 10,
    ) -> PSICalculationResult:
        """Calculates Population Stability Index (PSI) between baseline and sliding inference window."""
        exp_arr = np.asarray(expected_distribution, dtype=float)
        act_arr = np.asarray(actual_distribution, dtype=float)

        if len(exp_arr) == 0 or len(act_arr) == 0:
            raise ValueError("Distribution samples cannot be empty")

        # Robust uniform bin edges across combined support to avoid zero-width quantile collapses
        min_val = min(float(np.min(exp_arr)), float(np.min(act_arr)))
        max_val = max(float(np.max(exp_arr)), float(np.max(act_arr)))
        if min_val == max_val:
            min_val -= 0.5
            max_val += 0.5
        bins = np.linspace(min_val - 1e-4, max_val + 1e-4, num_bins + 1)

        # Bin counts with Laplace smoothing (+ 1e-4) to prevent log(0) or div/0
        exp_counts, _ = np.histogram(exp_arr, bins=bins)
        act_counts, _ = np.histogram(act_arr, bins=bins)

        exp_pct = (exp_counts + 1e-4) / (len(exp_arr) + 1e-4 * num_bins)
        act_pct = (act_counts + 1e-4) / (len(act_arr) + 1e-4 * num_bins)

        # PSI = sum((Actual_i - Expected_i) * ln(Actual_i / Expected_i))
        psi_contributions = (act_pct - exp_pct) * np.log(act_pct / exp_pct)
        psi_score = float(np.sum(psi_contributions))

        severity = (
            "SIGNIFICANT_DRIFT"
            if psi_score >= self.PSI_DRIFT_THRESHOLD
            else "MODERATE_SHIFT"
            if psi_score >= self.PSI_STABLE_THRESHOLD
            else "STABLE"
        )

        return PSICalculationResult(
            feature_name=feature_name,
            psi_score=round(psi_score, 4),
            severity=severity,
            bin_counts_expected=exp_counts.tolist(),
            bin_counts_actual=act_counts.tolist(),
            is_drift_detected=psi_score >= self.PSI_STABLE_THRESHOLD,
        )

    def calculate_brier_score(
        self,
        predicted_probabilities: Sequence[float],
        actual_outcomes: Sequence[int],
    ) -> float:
        """Calculates Brier calibration score: (1/N) * sum((prob - outcome)^2).

        Lower is better (0.0 represents perfect probabilistic calibration).
        """
        preds = np.asarray(predicted_probabilities, dtype=float)
        acts = np.asarray(actual_outcomes, dtype=float)

        if len(preds) != len(acts):
            raise ValueError(
                "Predicted probabilities and actual outcomes must have identical length"
            )

        brier = float(np.mean((preds - acts) ** 2))
        return round(brier, 4)
