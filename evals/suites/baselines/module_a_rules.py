"""Module A Baseline: Static Threshold Rules for Client AML (T033).

Baseline to beat: Static threshold rules (deposit/amount > X, velocity > Y).
Metrics & pre-registered target: PR-AUC, FPR (False Positive Rate) on legitimate high-volume traders.
Candidate model commitment: >= 30% relative reduction in FPR vs baseline at fixed recall.
"""

from typing import Any

import numpy as np

from eios.evals.metrics import compute_brier_score, compute_pr_auc


class RuleBasedAMLBaseline:
    """Static threshold rule engine for transaction alerting."""

    def __init__(self, amount_threshold: float = 10000.0, velocity_threshold: int = 5) -> None:
        self.amount_threshold = amount_threshold
        self.velocity_threshold = velocity_threshold

    def predict_proba(self, transactions: list[dict[str, Any]]) -> list[float]:
        scores: list[float] = []
        for tx in transactions:
            amt = float(tx.get("amount", 0.0))
            vel = int(tx.get("velocity_1h", 0))

            amt_flag = amt >= self.amount_threshold
            vel_flag = vel >= self.velocity_threshold

            if amt_flag and vel_flag:
                score = 0.90
            elif amt_flag:
                score = 0.45
            elif vel_flag:
                score = 0.40
            else:
                score = 0.10
            scores.append(score)
        return scores


def score_aml_transactions(transactions: list[dict[str, Any]]) -> dict[str, float]:
    baseline = RuleBasedAMLBaseline()
    scores = baseline.predict_proba(transactions)
    y_true = [int(tx.get("is_sar", 0)) for tx in transactions]

    pr_auc = compute_pr_auc(y_true, scores)
    brier = compute_brier_score(y_true, scores)

    # Compute False Positive Rate at default decision threshold 0.5
    y_arr = np.array(y_true)
    s_arr = np.array(scores)
    negatives = y_arr == 0
    total_negatives = int(np.sum(negatives))
    if total_negatives == 0:
        fpr = 0.0
    else:
        false_positives = int(np.sum((s_arr >= 0.5) & negatives))
        fpr = float(false_positives / total_negatives)

    return {
        "pr_auc": pr_auc,
        "brier_score": brier,
        "fpr": fpr,
    }
