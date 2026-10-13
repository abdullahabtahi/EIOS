"""Naive baseline rule-based churn predictor (Constitution Principle VI / T006).

Implements the pre-registered baseline: "no login > 14 days = churn".
Used as the benchmark that the Discrete-Time Hazard Model must beat by >= 0.10 PR-AUC.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


class NaiveRuleBaseline:
    """Baseline heuristic predicting churn based on consecutive inactive days."""

    def __init__(self, inactivity_threshold_days: int = 14) -> None:
        self.inactivity_threshold_days = inactivity_threshold_days

    def predict_proba(self, inactive_days: pd.Series | np.ndarray) -> np.ndarray:
        """Assign continuous risk probability scaling with inactive days.

        Partners with inactivity >= threshold get 1.0; others get inactive_days / (2 * threshold).
        """
        arr = np.asarray(inactive_days, dtype=float)
        probs = np.where(
            arr >= self.inactivity_threshold_days, 1.0, arr / (2.0 * self.inactivity_threshold_days)
        )
        return np.clip(probs, 0.0, 1.0)

    def predict(self, inactive_days: pd.Series | np.ndarray) -> np.ndarray:
        """Binary prediction: 1 if inactive_days >= threshold else 0."""
        arr = np.asarray(inactive_days, dtype=float)
        return (arr >= self.inactivity_threshold_days).astype(int)

    def evaluate(self, y_true: np.ndarray, y_score: np.ndarray) -> dict[str, float]:
        """Compute PR-AUC, AUROC, and Brier score for the baseline."""
        pr_auc = float(average_precision_score(y_true, y_score))
        try:
            auroc = float(roc_auc_score(y_true, y_score))
        except ValueError:
            auroc = 0.5
        brier = float(brier_score_loss(y_true, y_score))

        return {
            "pr_auc": pr_auc,
            "auroc": auroc,
            "brier_score": brier,
        }
