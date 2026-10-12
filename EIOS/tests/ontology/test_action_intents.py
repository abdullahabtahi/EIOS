"""Test Governed Action Intent Hub lifecycle and Four-Eyes policy (T038)."""

from datetime import UTC, datetime, timedelta

import pytest

from eios.ontology.actions.intent_hub import (
    ActionIntentHub,
    ActionIntentToken,
    ActionSeverity,
    ActionStatus,
    FourEyesApprovalRequiredError,
    InvalidActionParameterError,
    NonceReplayError,
    TokenExpiredError,
)


def test_propose_action_generates_signed_pending_token():
    hub = ActionIntentHub()
    token = hub.propose_action(
        action_type="FreezeAccount",
        parameters={"client_id": "C-1001", "reason_code": "MIRROR_TRADING"},
        evidence_refs=["EVID-101", "EVID-102"],
        requester_agent_id="SentinelAML",
    )

    assert isinstance(token, ActionIntentToken)
    assert token.status == ActionStatus.PENDING
    assert token.severity == ActionSeverity.HIGH
    assert token.signature is not None
    assert len(token.nonce) >= 16


def test_propose_action_validates_required_parameters():
    hub = ActionIntentHub()
    # FreezeAccount requires client_id and reason_code
    with pytest.raises(InvalidActionParameterError):
        hub.propose_action(
            action_type="FreezeAccount",
            parameters={"invalid_param": "foo"},
            evidence_refs=["EVID-1"],
        )


def test_action_intent_nonce_replay_prevention():
    hub = ActionIntentHub()
    token = hub.propose_action(
        action_type="HoldWithdrawal",
        parameters={"txn_id": "TXN-99", "reason": "VELOCITY_SPIKE"},
        evidence_refs=["EVID-1"],
    )

    # Attempting to register another intent with the same nonce
    with pytest.raises(NonceReplayError):
        hub._register_nonce(token.nonce)


def test_four_eyes_approval_enforcement_on_high_severity():
    hub = ActionIntentHub()
    token = hub.propose_action(
        action_type="FreezeAccount",
        parameters={"client_id": "C-1001", "reason_code": "MIRROR_TRADING"},
        evidence_refs=["EVID-1"],
    )
    assert token.severity == ActionSeverity.HIGH

    # First approval by Officer A
    updated_1 = hub.approve_action(token.intent_id, approver_id="OFFICER_A", role="MLRO")
    assert updated_1.status == ActionStatus.PENDING  # Needs 2nd approver for HIGH severity!

    # Attempting to execute with only 1 approver raises FourEyesApprovalRequiredError
    with pytest.raises(FourEyesApprovalRequiredError):
        hub.execute_action(token.intent_id)

    # Second approval by Officer B (different identity)
    updated_2 = hub.approve_action(token.intent_id, approver_id="OFFICER_B", role="COMPLIANCE_HEAD")
    assert updated_2.status == ActionStatus.APPROVED

    # Now execution succeeds
    exec_result = hub.execute_action(token.intent_id)
    assert exec_result.status == ActionStatus.EXECUTED


def test_expired_token_cannot_be_approved():
    hub = ActionIntentHub()
    token = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={"partner_ids": ["P-101"], "playbook_id": "VIP_BONUS", "budget": 5000.0},
        evidence_refs=["EVID-2"],
    )

    # Manually expire the token
    hub._tokens[token.intent_id].expires_at = datetime.now(UTC) - timedelta(minutes=1)

    with pytest.raises(TokenExpiredError):
        hub.approve_action(token.intent_id, approver_id="MGR_1", role="PARTNER_LEAD")


def test_propose_action_with_propensity_score_and_causal_context():
    hub = ActionIntentHub()
    token = hub.propose_action(
        action_type="FreezeAccount",
        parameters={"client_id": "C-2002", "reason_code": "SMURFING_CLUSTER"},
        evidence_refs=["EVID-201"],
        requester_agent_id="SentinelAML",
        propensity_score=0.88,
        causal_context={"graph_density": 0.92, "flow_velocity_usd_hr": 450000.0},
    )
    assert token.propensity_score == 0.88
    assert token.causal_context["graph_density"] == 0.92
    assert token.causal_context["flow_velocity_usd_hr"] == 450000.0


def test_action_intent_hub_with_sequencer_and_hot_state():
    from eios.ingestion.hot_state import HotStateEngine
    from eios.ontology.actions.sequencer import LedgerSequencer

    engine = HotStateEngine(db_path=":memory:")
    sequencer = LedgerSequencer(hot_state_engine=engine)
    hub = ActionIntentHub(sequencer=sequencer, hot_state_engine=engine)

    # 1. Propose
    token = hub.propose_action(
        action_type="HoldWithdrawal",
        parameters={"txn_id": "TXN-888", "reason": "HIGH_RISK_MULE"},
        evidence_refs=["EVID-888"],
    )
    assert token.ledger_seq == 1
    assert sequencer.current_seq == 1

    # 2. Approve 1 (Four-Eyes first approval)
    hub.approve_action(
        token.intent_id,
        approver_id="OFFICER_1",
        role="MLRO",
        comment="Reviewing mule evidence",
        override_applied=True,
        override_reason="Escalated to Tier 3 scrutiny",
    )
    assert sequencer.current_seq == 2
    token_pending = hub.get_status(token.intent_id)
    assert token_pending.status == ActionStatus.PENDING
    assert token_pending.approvals[0].override_applied is True

    # 3. Approve 2 (Distinct officer)
    hub.approve_action(
        token.intent_id,
        approver_id="OFFICER_2",
        role="COMPLIANCE_HEAD",
        comment="Confirmed mule ring link",
    )
    assert sequencer.current_seq == 3
    token_approved = hub.get_status(token.intent_id)
    assert token_approved.status == ActionStatus.APPROVED

    # 4. Execute
    hub.execute_action(token.intent_id)
    assert sequencer.current_seq == 4
    token_exec = hub.get_status(token.intent_id)
    assert token_exec.status == ActionStatus.EXECUTED

    # 5. Check hot state persistence
    cursor = engine.get_cursor()
    row = cursor.execute(
        "SELECT intent_id, action_type, status, ledger_seq FROM governed_action_intents WHERE intent_id = ?",
        [token.intent_id],
    ).fetchone()
    assert row is not None
    assert row[0] == token.intent_id
    assert row[1] == "HoldWithdrawal"
    assert row[2] == "EXECUTED"
    assert row[3] == 4


def test_reject_action_lifecycle():
    from eios.ontology.actions.sequencer import LedgerSequencer

    sequencer = LedgerSequencer()
    hub = ActionIntentHub(sequencer=sequencer)

    token = hub.propose_action(
        action_type="SuspendPartner",
        parameters={"partner_id": "P-999", "scope": "FULL"},
        evidence_refs=["ALERT-999"],
    )
    assert token.status == ActionStatus.PENDING

    rejected_token = hub.reject_action(
        token.intent_id,
        approver_id="VP_COMPLIANCE",
        role="EXECUTIVE",
        reason="Insufficient evidence of willful partner complicity",
    )
    assert rejected_token.status == ActionStatus.REJECTED
    assert sequencer.current_seq == 2

