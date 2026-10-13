"""Tests for Scenario Sandboxing, Drift Surveillance, and Four-Eyes Outbox (F019 Phase 8)."""

import pytest

from eios.monitoring.drift_surveillance import DriftSurveillanceEngine
from eios.ontology.actions.outbox_ledger import (
    FourEyesViolationError,
    OutboxState,
    PersistentActionOutboxLedger,
)
from eios.ontology.branching.scenario_sandbox import ScenarioSandboxEngine


def test_scenario_sandbox_branching_and_isolation():
    engine = ScenarioSandboxEngine()

    # Fork new branch with shock parameters
    branch = engine.fork_branch(
        scenario_name="Aggressive Fee Hike",
        operator_id="OFFICER_CHENG",
        shock_parameters={"spread_markup_bps": 15.0},
    )

    assert branch.scenario_name == "Aggressive Fee Hike"
    assert branch.parent_branch_id == "main"

    # Branch has new value
    assert engine.read_state(branch.branch_id, "spread_markup_bps") == 15.0

    # Canonical 'main' is UNTOUCHED
    assert engine.read_state("main", "spread_markup_bps") is None

    # Cannot mutate 'main' directly
    with pytest.raises(PermissionError):
        engine.mutate_state("main", "spread_markup_bps", 99.0)

    # Compute diff
    diff = engine.compute_branch_diff(branch.branch_id)
    assert "spread_markup_bps" in diff
    assert diff["spread_markup_bps"]["sandbox_value"] == 15.0


def test_drift_surveillance_psi_and_brier():
    surveillance = DriftSurveillanceEngine()

    # Identical distributions -> Stable PSI < 0.10
    base_dist = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] * 20
    test_stable = [0.11, 0.21, 0.29, 0.41, 0.49, 0.61, 0.71, 0.79, 0.91, 0.99] * 20

    res_stable = surveillance.calculate_psi(base_dist, test_stable)
    assert res_stable.is_drift_detected is False
    assert res_stable.severity == "STABLE"

    # Severe distribution shift -> Significant Drift PSI >= 0.25
    test_drifted = [0.9, 0.92, 0.95, 0.98, 0.99] * 40
    res_drift = surveillance.calculate_psi(base_dist, test_drifted)
    assert res_drift.is_drift_detected is True
    assert res_drift.severity == "SIGNIFICANT_DRIFT"

    # Brier calibration score calculation
    preds = [0.9, 0.8, 0.1, 0.2]
    acts = [1, 1, 0, 0]
    brier = surveillance.calculate_brier_score(preds, acts)
    assert brier < 0.05  # Highly calibrated


def test_four_eyes_outbox_state_machine():
    outbox = PersistentActionOutboxLedger()

    # Stage intent
    rec = outbox.stage_intent(
        action_type="FreezeAccount",
        target_entity_id="ACC-84920",
        initiator_id="OFFICER_INITIATOR",
    )
    assert rec.state == OutboxState.PENDING_PRIMARY_APPROVAL

    # Initiator cannot self-approve
    with pytest.raises(FourEyesViolationError):
        outbox.submit_primary_approval(rec.intent_id, "OFFICER_INITIATOR", "COMPLIANCE_OFFICER")

    # Primary approval succeeds with distinct officer
    outbox.submit_primary_approval(rec.intent_id, "OFFICER_ALICE", "COMPLIANCE_OFFICER")
    assert rec.state == OutboxState.PENDING_SECONDARY_APPROVAL

    # Same approver cannot give second approval
    with pytest.raises(FourEyesViolationError):
        outbox.submit_secondary_approval(rec.intent_id, "OFFICER_ALICE", "MLRO_HEAD")

    # Same role cannot give second approval
    with pytest.raises(FourEyesViolationError):
        outbox.submit_secondary_approval(rec.intent_id, "OFFICER_BOB", "COMPLIANCE_OFFICER")

    # Valid second approval with distinct officer AND distinct role commits intent!
    committed = outbox.submit_secondary_approval(rec.intent_id, "OFFICER_BOB", "MLRO_HEAD")
    assert committed.state == OutboxState.COMMITTED
    assert committed.ledger_seq == 1
    assert committed.hash_chain is not None

    # Verified exported into BigQuery Lakehouse sync buffer
    bq_rows = outbox.bq_exporter.get_buffered_rows()
    assert len(bq_rows) == 1
    assert bq_rows[0]["ledger_seq"] == 1
