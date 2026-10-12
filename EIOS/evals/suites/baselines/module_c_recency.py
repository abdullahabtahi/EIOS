"""Module C Baseline: Recency Inactivity Rule for Partner Churn (T035).

Baseline to beat: Static inactivity threshold ("No login for N days").
Candidate model commitment: Discrete-time hazard model achieving PR-AUC >= baseline + 0.10,
and median lead time >= baseline + 7 days.
"""

from typing import Any

import numpy as np

from eios.evals.metrics import compute_pr_auc


class RecencyChurnBaseline:
    """Predicts partner churn probability purely from login recency."""

    def __init__(self, inactivity_threshold_days: int = 14) -> None:
        self.inactivity_threshold = inactivity_threshold_days

    def predict_proba(self, partners: list[dict[str, Any]]) -> list[float]:
        scores: list[float] = []
        for p in partners:
            days = float(p.get("days_since_last_login", 0))
            if days >= self.inactivity_threshold:
                score = min(0.95, 0.50 + (days - self.inactivity_threshold) * 0.03)
            else:
                score = max(0.05, (days / self.inactivity_threshold) * 0.40)
            scores.append(float(score))
        return scores


def evaluate_recency_churn(partners: list[dict[str, Any]]) -> dict[str, float]:
    baseline = RecencyChurnBaseline()
    scores = baseline.predict_proba(partners)
    y_true = [int(p.get("churned_30d", 0)) for p in partners]

    pr_auc = compute_pr_auc(y_true, scores)

    # Calculate lead times for churned partners flagged by baseline
    lead_times: list[float] = []
    for p, s in zip(partners, scores, strict=False):
        if p.get("churned_30d") == 1 and s >= 0.5:
            actual_day = p.get("actual_churn_day")
            login_gap = p.get("days_since_last_login", 0)
            if actual_day is not None and actual_day >= login_gap:
                lead_times.append(float(actual_day - login_gap))
            else:
                lead_times.append(5.0)  # Default fallback lead time

    median_lead_time = float(np.median(lead_times)) if lead_times else 0.0

    return {
        "pr_auc": pr_auc,
        "median_lead_time_days": median_lead_time,
    }
