"""Unit and Chaos Fault Injection tests for Simulated Core Write-Back Sink (US3)."""

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.intent_hub import ActionIntentHub, ActionStatus
from eios.ontology.actions.models import ExecutionReceipt, ExecutionStatus
from eios.ontology.actions.sequencer import LedgerSequencer
from eios.ontology.actions.sink import FaultMode, SimulatedWriteBackSink
import pytest


def test_simulated_sink_normal_execution_commits_action():
    engine = HotStateEngine(db_path=":memory:")
    sequencer = LedgerSequencer(hot_state_engine=engine)
    sink = SimulatedWriteBackSink(sequencer=sequencer, hot_state_engine=engine)
    hub = ActionIntentHub(sequencer=sequencer, sink=sink, hot_state_engine=engine)

    # Propose & approve
    token = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={"partner_ids": ["P-101"], "playbook_id": "RETAIN_TIER1", "budget": 1200.0},
        evidence_refs=["CHURN-ALERT-1"],
    )
    hub.approve_action(token.intent_id, approver_id="MGR_1", role="PARTNER_LEAD")

    # Execute against sink
    receipt = hub.execute_action(token.intent_id)

    assert isinstance(receipt, ExecutionReceipt)
    assert receipt.status == ExecutionStatus.COMMITTED
    assert receipt.intent_id == token.intent_id
    assert receipt.external_transaction_id.startswith("SIM-CORE-TXN-")
    assert receipt.simulated_latency_ms >= 0.0

    # Token state updated
    updated_token = hub.get_status(token.intent_id)
    assert updated_token.status == ActionStatus.EXECUTED
    assert updated_token.execution_receipt_id == receipt.receipt_id

    # Hot state persistence verified
    cursor = engine.get_cursor()
    row = cursor.execute(
        "SELECT receipt_id, intent_id, status FROM simulated_writeback_ledger WHERE receipt_id = ?",
        [receipt.receipt_id],
    ).fetchone()
    assert row is not None
    assert row[1] == token.intent_id
    assert row[2] == "COMMITTED"


def test_simulated_sink_idempotency_prevents_duplicate_mutations():
    sequencer = LedgerSequencer()
    sink = SimulatedWriteBackSink(sequencer=sequencer)
    hub = ActionIntentHub(sequencer=sequencer, sink=sink)

    token = hub.propose_action(
        action_type="AdjustPartnerTier",
        parameters={"partner_id": "P-202", "target_tier": 2},
        evidence_refs=["PERF-EVID-1"],
    )
    hub.approve_action(token.intent_id, "LEAD_1", "PARTNER_LEAD")

    idempotency_key = "IDEMPOTENT-CALL-12345"

    # First execution
    receipt_1 = hub.execute_action(token.intent_id, idempotency_key=idempotency_key)
    # Second execution with same idempotency key (even if token is already EXECUTED)
    receipt_2 = sink.commit_action(token, idempotency_key=idempotency_key)

    assert receipt_1.receipt_id == receipt_2.receipt_id
    assert receipt_1.external_transaction_id == receipt_2.external_transaction_id
    assert receipt_1.executed_at == receipt_2.executed_at
    # Ensure idempotency cache did not double-record in sequencer
    assert len(sink.get_execution_history()) == 1


def test_simulated_sink_network_timeout_fault_aborts_action_with_compensation():
    engine = HotStateEngine(db_path=":memory:")
    sequencer = LedgerSequencer(hot_state_engine=engine)
    sink = SimulatedWriteBackSink(sequencer=sequencer, hot_state_engine=engine)
    hub = ActionIntentHub(sequencer=sequencer, sink=sink, hot_state_engine=engine)

    token = hub.propose_action(
        action_type="HoldWithdrawal",
        parameters={"txn_id": "TXN-FAULT-1", "reason": "VELOCITY_SPIKE"},
        evidence_refs=["ALERT-999"],
    )
    hub.approve_action(token.intent_id, "OFF_1", "MLRO")
    hub.approve_action(token.intent_id, "OFF_2", "HEAD_OF_COMPLIANCE")

    # Inject network timeout chaos fault
    sink.set_fault_mode(FaultMode.NETWORK_TIMEOUT)

    receipt = hub.execute_action(token.intent_id)

    assert receipt.status == ExecutionStatus.ABORTED
    assert receipt.compensation_intent_id is not None
    assert hub.get_status(token.intent_id).status == ActionStatus.ABORTED

    # Sequencer records compensation / abort event
    abort_entries = sequencer.get_entries_by_event("ACTION_ABORTED")
    assert len(abort_entries) == 1
    assert abort_entries[0].payload["compensation_intent_id"] == receipt.compensation_intent_id


def test_simulated_sink_ledger_conflict_and_core_rejection_modes():
    sequencer = LedgerSequencer()
    sink = SimulatedWriteBackSink(sequencer=sequencer)
    hub = ActionIntentHub(sequencer=sequencer, sink=sink)

    # 1. LEDGER_CONFLICT
    token_1 = hub.propose_action(
        action_type="ReviewSpreadPricing",
        parameters={"symbol": "EURUSD", "target_spread_pips": 1.0},
        evidence_refs=["EVID-1"],
    )
    hub.approve_action(token_1.intent_id, "OFF_1", "LEAD")
    sink.set_fault_mode(FaultMode.LEDGER_CONFLICT)
    receipt_conflict = hub.execute_action(token_1.intent_id)
    assert receipt_conflict.status == ExecutionStatus.ABORTED

    # 2. CORE_REJECTION
    sink.set_fault_mode(FaultMode.CORE_REJECTION)
    token_2 = hub.propose_action(
        action_type="ReviewSpreadPricing",
        parameters={"symbol": "GBPUSD", "target_spread_pips": 1.5},
        evidence_refs=["EVID-2"],
    )
    hub.approve_action(token_2.intent_id, "OFF_1", "LEAD")
    receipt_rejection = hub.execute_action(token_2.intent_id)
    assert receipt_rejection.status == ExecutionStatus.REJECTED
