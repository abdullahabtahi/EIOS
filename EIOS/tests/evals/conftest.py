"""Shared fixtures for EIOS evaluation harness tests (F04)."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_predictions() -> tuple[list[float], list[int]]:
    """Sample predicted probabilities and binary ground-truth labels."""
    y_true = [0, 0, 1, 1, 0, 1, 0, 1, 1, 0]
    y_pred = [0.1, 0.2, 0.8, 0.9, 0.3, 0.7, 0.25, 0.85, 0.95, 0.05]
    return y_pred, y_true


@pytest.fixture
def sample_time_series() -> tuple[list[float], list[float]]:
    """Sample actual values and forecast values for MASE evaluation."""
    y_actual = [100.0, 105.0, 102.0, 108.0, 110.0, 115.0, 112.0, 120.0]
    y_pred = [99.0, 104.0, 103.0, 107.0, 111.0, 114.0, 113.0, 119.0]
    return y_actual, y_pred


@pytest.fixture
def mock_eval_truth_dir(tmp_path: Path) -> Path:
    """Mock ground truth storage directory simulating eval-truth/ bucket."""
    truth_dir = tmp_path / "eval-truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = truth_dir / "manifest_seed_101.json"
    manifest_file.write_text(
        '{"seed": 101, "fraud_rings": ["R-1", "R-2"], "churn_partners": ["P-10"]}',
        encoding="utf-8",
    )
    return truth_dir
