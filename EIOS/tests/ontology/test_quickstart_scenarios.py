"""End-to-End Quickstart Scenario Validation for Feature 011 (T039).

Executes and verifies Scenarios 1 through 6 defined in specs/011-governed-actions-ledger/quickstart.md.
"""

import pytest

from eios.conversation.specialists.governance import GovernanceAuditorSpecialist
from eios.ontology.actions.audit import ContinuousAuditWalker
from eios.ontology.actions.intent_hub import (
    ActionIntentHub,
    ActionSeverity,
    ActionStatus,
    FourEyesApprovalRequiredError,
)
from eios.ontology.actions.outcomes import DecisionOutcomesStore
from eios.ontology.actions.sequencer import LedgerSequencer
from eios.ontology.actions.sink import FaultMode, SimulatedWriteBackSink
from eios.ontology.actions.worm import WORMAnchorService
from eios.ontology.omcp.server import OMCPServer


def test_quickstart_scenario_1_two_phase_commit_four_eyes():
    """Scenario 1: Two-Phase Commit with Four-Eyes Dual Approval (High Severity)."""
    sequencer = LedgerSequencer()
    sink = SimulatedWriteBackSink(sequencer=sequencer)
    hub = ActionIntentHub(sequencer=sequencer, sink=sink)

    # 1. Propose high-severity HoldWithdrawal
    token = hub.propose_action(
        action_type="HoldWithdrawal",
        parameters={"txn_id": "TXN-90210", "reason": "STRUCTURING_VELOCITY_SPIKE"},
        evidence_refs=["ALERT-AML-501", "DOSSIER-C-1002"],
        requester_agent_id="SentinelAMLSpecialist",
        propensity_score=0.92,
        causal_context={"deposit_velocity": 4.5, "turnover_ratio": 0.02},
    )

    assert token.status == ActionStatus.PENDING
    assert token.severity == ActionSeverity.HIGH
    assert token.requires_dual_approval is True
    assert token.signature is not None

    # 2. Compliance Officer 1 approves
    hub.approve_action(
        token.intent_id, approver_id="OFFICER_A", role="MLRO", comment="Flagged structuring"
    )
    token = hub.get_status(token.intent_id)
    assert token.status == ActionStatus.PENDING  # Still PENDING: Four-Eyes mandated!

    # 3. Premature execution attempt MUST be blocked
    with pytest.raises(FourEyesApprovalRequiredError):
        hub.execute_action(token.intent_id)

    # 4. Distinct Senior Officer approves
    hub.approve_action(
        token.intent_id, approver_id="OFFICER_B", role="HEAD_OF_COMPLIANCE", comment="Confirmed"
    )
    token = hub.get_status(token.intent_id)
    assert token.status == ActionStatus.APPROVED

    # 5. Execute against Simulated Core Write-Back Sink
    receipt = hub.execute_action(token.intent_id)
    assert receipt.status == "COMMITTED"
    assert receipt.external_transaction_id.startswith("SIM-CORE-")
    token = hub.get_status(token.intent_id)
    assert token.status == ActionStatus.EXECUTED


def test_quickstart_scenario_2_policy_fast_path():
    """Scenario 2: Policy Fast-Path for Operational Actions (budget <= $2,500.00)."""
    sequencer = LedgerSequencer()
    sink = SimulatedWriteBackSink(sequencer=sequencer)
    hub = ActionIntentHub(sequencer=sequencer, sink=sink)

    # Propose retention playbook within threshold ($1,500 <= $2,500)
    token = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={"partner_ids": ["P-88"], "playbook_id": "TIER_2_RETENTION", "budget": 1500.0},
        evidence_refs=["CHURN-ALERT-77"],
        requester_agent_id="ChurnRetentionAgent",
    )

    assert token.requires_dual_approval is False
    assert "FAST_PATH_ELIGIBLE" in token.policy_tags

    # Single manager approval immediately unlocks commit phase
    hub.approve_action(token.intent_id, approver_id="MGR_1", role="PARTNER_LEAD")
    assert hub.get_status(token.intent_id).status == ActionStatus.APPROVED

    # Commit executes cleanly
    receipt = hub.execute_action(token.intent_id)
    assert receipt.status == "COMMITTED"


def test_quickstart_scenario_3_idempotency_and_chaos():
    """Scenario 3: Idempotent Execution & Chaos Fault Injection."""
    sequencer = LedgerSequencer()
    sink = SimulatedWriteBackSink(sequencer=sequencer)
    hub = ActionIntentHub(sequencer=sequencer, sink=sink)

    token = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={"partner_ids": ["P-88"], "playbook_id": "TIER_2_RETENTION", "budget": 1000.0},
        evidence_refs=["CHURN-ALERT-77"],
        requester_agent_id="ChurnRetentionAgent",
    )
    hub.approve_action(token.intent_id, approver_id="MGR_1", role="PARTNER_LEAD")

    # 1. Test Idempotency: Resubmit executed token with same idempotency key
    idempotency_key = f"IDEM-{token.intent_id}"
    receipt_1 = hub.execute_action(token.intent_id, idempotency_key=idempotency_key)
    receipt_2 = hub.execute_action(token.intent_id, idempotency_key=idempotency_key)

    assert receipt_1.receipt_id == receipt_2.receipt_id
    assert receipt_1.external_transaction_id == receipt_2.external_transaction_id

    # 2. Chaos Fault Injection: Simulate Core Banking Gateway Timeout
    sink.set_fault_mode(FaultMode.NETWORK_TIMEOUT)

    fault_token = hub.propose_action(
        action_type="FreezeAccount",
        parameters={"client_id": "C-999", "reason_code": "FRAUD_CONFIRMED"},
        evidence_refs=["EVID-999"],
    )
    hub.approve_action(fault_token.intent_id, "OFF_1", "MLRO")
    hub.approve_action(fault_token.intent_id, "OFF_2", "HEAD")

    # Execution encounters fault
    abort_receipt = hub.execute_action(fault_token.intent_id)
    assert abort_receipt.status == "ABORTED"
    assert hub.get_status(fault_token.intent_id).status == ActionStatus.ABORTED

    # Verify compensation event logged
    comp_entries = sequencer.get_entries_by_event("ACTION_ABORTED")
    assert len(comp_entries) > 0


def test_quickstart_scenario_4_worm_and_continuous_audit_walker():
    """Scenario 4: Upstream Monotonic Sequencer, WORM Anchoring & Continuous Tamper Walker."""
    sequencer = LedgerSequencer()
    worm_service = WORMAnchorService(sequencer=sequencer)
    walker = ContinuousAuditWalker(sequencer=sequencer, worm_service=worm_service)

    # Populate several ledger entries
    from eios.ontology.actions.models import LedgerEventType

    for i in range(3):
        sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"ENT_{i}",
            payload={"step": i},
        )

    # 1. Periodic WORM Anchor Checkpoint
    checkpoint = worm_service.create_checkpoint()
    assert checkpoint.checkpoint_seq == 1
    assert checkpoint.compliance_mode is True
    assert checkpoint.chain_head_hash == sequencer.head_hash

    # 2. Continuous Audit Verification on Untampered Ledger
    report = walker.verify_ledger()
    assert report.is_valid is True
    assert report.integrity_score == 1.0
    assert report.tampered_sequence_id is None
    assert report.worm_checkpoints_verified >= 1

    # 3. Simulate Adversarial Database Tampering at Sequence 2
    sequencer.tamper_payload_for_testing(target_seq=2, corrupted_byte_key="step", corrupted_val=999)

    # 4. Continuous Audit Walker MUST detect tampering and pinpoint exact sequence index
    tamper_report = walker.verify_ledger()
    assert tamper_report.is_valid is False
    assert tamper_report.integrity_score < 1.0
    assert tamper_report.tampered_sequence_id == 2
    assert "MISMATCH" in tamper_report.failure_reason


def test_quickstart_scenario_5_outcomes_and_aipw():
    """Scenario 5: Multi-Horizon Decision Outcomes & Doubly Robust AIPW Tracking."""
    outcomes_store = DecisionOutcomesStore()

    # 1. Record decision context at proposal time
    outcome_record = outcomes_store.record_decision(
        intent_id="intent-test-quickstart-001",
        entity_id="P-88",
        action_type="LaunchRetentionPlaybook",
        treatment_assigned=1,
        propensity_score=0.84,
        causal_features={"tier": 2, "churn_risk": 0.65, "tenure_months": 18},
        manager_override_flag=True,
        override_reason="Strategic VIP account - reduced budget from $2500 to $1500",
    )

    assert outcome_record.manager_override_flag is True
    assert outcome_record.propensity_score == 0.84

    # 2. Reconcile forward actuals at elapsed horizons (30d, 60d, 90d)
    reconciled = outcomes_store.reconcile_outcomes(
        outcome_id=outcome_record.outcome_id,
        observed_retained_revenue_30d=4200.0,
        observed_retained_revenue_60d=8900.0,
        actual_churn_60d=False,
        clawback_recovered_usd_90d=0.0,
    )

    assert reconciled.observed_retained_revenue_60d == 8900.0
    assert reconciled.actual_churn_60d is False


def test_quickstart_scenario_6_omcp_and_replay_fallback(seeded_hot_state):
    """Scenario 6: OMCP Governance Tools & Deterministic Replay Fallback."""
    omcp = OMCPServer(hot_state=seeded_hot_state)
    audit_status = omcp.call_tool("get_ledger_audit_status", {}, caller_role="ComplianceAuditor")
    assert "head_seq" in audit_status
    assert "integrity_score" in audit_status

    # Test Governance Conversational Specialist Replay Fallback
    specialist = GovernanceAuditorSpecialist(omcp_server=omcp)
    response = specialist.handle_query(
        query="What is the cryptographic health of our action ledger?",
        simulate_llm_outage=True,
    )

    assert "[REPLAY]" in response["content"]
    assert "Cryptographic Ledger Status" in response["content"]
    assert response["is_fallback"] is True
