"""Core evaluation framework and statistical metrics engine for EIOS (F04)."""

from eios.evals.isolation import GroundTruthAccessDeniedError, read_ground_truth
from eios.evals.metrics import (
    bootstrap_confidence_interval,
    compute_brier_score,
    compute_lift,
    compute_mase,
    compute_pr_auc,
)
from eios.evals.models import (
    BaselineComparison,
    EvalReport,
    GoldenDialogueScenario,
    GoldenDialogueTurn,
    MetricConfidenceInterval,
    RedLineID,
    RedLineResult,
    SeedManifest,
    Tier,
)

__all__ = [
    "compute_pr_auc",
    "compute_brier_score",
    "compute_mase",
    "compute_lift",
    "bootstrap_confidence_interval",
    "GroundTruthAccessDeniedError",
    "read_ground_truth",
    "Tier",
    "RedLineID",
    "MetricConfidenceInterval",
    "RedLineResult",
    "BaselineComparison",
    "SeedManifest",
    "GoldenDialogueTurn",
    "GoldenDialogueScenario",
    "EvalReport",
]
