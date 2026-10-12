"""Test IAM and process boundary guard for eval-truth storage (T007, ADR-015)."""

from pathlib import Path

import pytest

from eios.evals.isolation import GroundTruthAccessDeniedError, read_ground_truth


def test_agent_role_cannot_read_ground_truth(mock_eval_truth_dir: Path):
    with pytest.raises(GroundTruthAccessDeniedError) as exc_info:
        read_ground_truth(
            truth_dir=mock_eval_truth_dir,
            filename="manifest_seed_101.json",
            caller_role="sa-reasoning-mesh",
        )
    assert "Access denied" in str(exc_info.value)
    assert "sa-reasoning-mesh" in str(exc_info.value)


def test_eval_harness_role_can_read_ground_truth(mock_eval_truth_dir: Path):
    data = read_ground_truth(
        truth_dir=mock_eval_truth_dir,
        filename="manifest_seed_101.json",
        caller_role="sa-eval-harness",
    )
    assert data["seed"] == 101
    assert "fraud_rings" in data
