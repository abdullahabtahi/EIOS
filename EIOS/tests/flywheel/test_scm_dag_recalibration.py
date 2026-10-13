"""Tests for User Story 3: Automated SCM DAG Edge-Weight Recalibration."""

import pytest

from eios.flywheel.models import SCMRecalibrationCheckpoint
from eios.flywheel.schemas import validate_contract


def test_scm_recalibration_reduces_mae():
    from eios.flywheel.recalibration import SCMRecalibrator

    # Initial graph: competitor_payout -> partner_churn -> net_deposits
    initial_weights = {
        "competitor_payout_rate->partner_churn_rate": 0.45,
        "partner_churn_rate->net_deposit_volume_usd": -12000.0,
    }

    recalibrator = SCMRecalibrator(
        initial_weights=initial_weights,
        learning_rate=0.05,
        l2_reg=0.01,
        weight_bounds=(-20000.0, 20000.0),
    )

    # Synthetic observations where actual churn is consistently higher than predicted
    # residual = actual - predicted > 0 -> gradient should push weight up
    observations = [
        {
            "edge": "competitor_payout_rate->partner_churn_rate",
            "source_val": 1.2,
            "residual": 0.15,
        }
        for _ in range(50)
    ]

    checkpoint = recalibrator.recalibrate_edges(
        observations=observations,
        version="v1.3.0",
        provenance_seed="seed-dag-test-001",
    )

    assert isinstance(checkpoint, SCMRecalibrationCheckpoint)
    assert checkpoint.is_acyclic is True
    # The edge weight should have shifted upward
    updated_weight = checkpoint.edge_weights["competitor_payout_rate->partner_churn_rate"]
    assert updated_weight > 0.45
    assert checkpoint.recalibrated_residuals_mae < checkpoint.baseline_residuals_mae


def test_scm_topological_acyclicity_check():
    from eios.flywheel.recalibration import SCMRecalibrator, verify_dag_acyclicity

    # Acyclic graph
    valid_edges = [
        ("A", "B"),
        ("B", "C"),
        ("A", "C"),
    ]
    assert verify_dag_acyclicity(valid_edges) is True

    # Cyclic graph
    cyclic_edges = [
        ("A", "B"),
        ("B", "C"),
        ("C", "A"),
    ]
    assert verify_dag_acyclicity(cyclic_edges) is False

    recalibrator = SCMRecalibrator(initial_weights={})
    with pytest.raises(ValueError, match="Directed cycle detected"):
        recalibrator.validate_acyclicity(["A->B", "B->C", "C->A"])


def test_scm_checkpoint_contract_validation():
    from eios.flywheel.recalibration import SCMRecalibrator

    recalibrator = SCMRecalibrator(initial_weights={"X->Y": 0.5})
    checkpoint = recalibrator.recalibrate_edges(
        observations=[{"edge": "X->Y", "source_val": 1.0, "residual": 0.1}],
        version="v1.3.1",
        provenance_seed="seed-contract-val",
    )

    dumped = checkpoint.model_dump(mode="json")
    assert validate_contract(dumped, "scm-recalibration-checkpoint") is True
