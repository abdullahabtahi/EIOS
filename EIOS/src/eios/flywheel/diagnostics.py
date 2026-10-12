"""Model Calibration Diagnostics Engine (ECE, Brier Score, Reliability Curves)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Sequence
import uuid
import numpy as np

from eios.flywheel.models import CalibrationDiagnosticsReport


class CalibrationDiagnosticsEngine:
    """Computes Expected Calibration Error (ECE), Brier scores, and drift alerts.

    Adheres to Constitution Principle I: all diagnostics are computed deterministically.
    Flags model drift whenever ECE exceeds the institutional 15% threshold (0.15).
    """

    def __init__(self, n_bins: int = 10, drift_threshold: float = 0.15) -> None:
        self.n_bins = n_bins
        self.drift_threshold = drift_threshold

    def evaluate_calibration(
        self,
        predicted_probs: Sequence[float] | np.ndarray,
        actual_labels: Sequence[float | int | bool] | np.ndarray,
        model_id: str = "default-model",
    ) -> CalibrationDiagnosticsReport:
        """Evaluates calibration quality over binary prediction outcomes."""
        p = np.asarray(predicted_probs, dtype=np.float64)
        y = np.asarray(actual_labels, dtype=np.float64)

        if len(p) != len(y):
            raise ValueError(
                f"Length mismatch: {len(p)} predicted probabilities vs {len(y)} actual labels"
            )

        n = len(p)
        if n == 0:
            return CalibrationDiagnosticsReport(
                report_id=str(uuid.uuid4()),
                model_id=model_id,
                timestamp=datetime.now(UTC),
                sample_count=0,
                expected_calibration_error=0.0,
                brier_score=0.0,
                reliability_bins=[],
                is_drift_detected=False,
            )

        # Clip predicted probabilities to [0, 1] for safety
        p = np.clip(p, 0.0, 1.0)
        y = np.clip(y, 0.0, 1.0)

        # Brier Score
        brier_score = float(np.mean((p - y) ** 2))

        # 10-bin Expected Calibration Error (ECE)
        bin_edges = np.linspace(0.0, 1.0, self.n_bins + 1)
        ece = 0.0
        bins_summary: List[Dict[str, Any]] = []

        for i in range(self.n_bins):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]

            if i == self.n_bins - 1:
                in_bin = (p >= lower) & (p <= upper)
            else:
                in_bin = (p >= lower) & (p < upper)

            bin_count = int(np.sum(in_bin))

            if bin_count > 0:
                bin_conf = float(np.mean(p[in_bin]))
                bin_acc = float(np.mean(y[in_bin]))
                gap = abs(bin_acc - bin_conf)
                ece += (bin_count / n) * gap
            else:
                bin_conf = float((lower + upper) / 2.0)
                bin_acc = 0.0
                gap = 0.0

            bins_summary.append({
                "bin_index": i + 1,
                "bin_lower": round(float(lower), 2),
                "bin_upper": round(float(upper), 2),
                "sample_count": bin_count,
                "mean_predicted_prob": round(bin_conf, 4),
                "empirical_frequency": round(bin_acc, 4),
                "calibration_gap": round(gap, 4),
            })

        is_drift = bool(ece > self.drift_threshold)

        return CalibrationDiagnosticsReport(
            report_id=str(uuid.uuid4()),
            model_id=model_id,
            timestamp=datetime.now(UTC),
            sample_count=n,
            expected_calibration_error=round(float(ece), 4),
            brier_score=round(float(brier_score), 4),
            reliability_bins=bins_summary,
            is_drift_detected=is_drift,
        )
