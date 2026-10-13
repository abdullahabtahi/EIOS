"""Unit and state machine tests for Governed Action Shelf (Phase 9: Two-Phase Commit & Four-Eyes)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from eios.cockpit.governance_shelf import GovernedActionShelf
from eios.cockpit.schemas import validate_contract
from eios.ontology.actions.models import (
    ActionIntentToken,
    ActionSeverity,
    ActionStatus,
)
from eios.ontology.actions.signer import LocalDevActionSigner


def _make_dummy_token(
    action_type: str = "HoldWithdrawal",
    severity: ActionSeverity = ActionSeverity.HIGH,
    requires_dual: bool = True,
    expires_in_seconds: int = 900,
) -> ActionIntentToken:
    now = datetime.now(UTC)
    return ActionIntentToken(
        intent_id=str(uuid.uuid4()),
        action_type=action_type,
        parameters={"txn_id": "tx_99812", "amount": 15000.0, "reason": "Structuring detected"},
        evidence_refs=["ev_roundtrip_881"],
        severity=severity,
        status=ActionStatus.PENDING,
        nonce="nonce_test_12345",
        issued_at=now,
        expires_at=now + timedelta(seconds=expires_in_seconds),
        requester_agent_id="AMLWorkerAgent",
        kms_key_id="projects/eios/locations/global/keyRings/rings/cryptoKeys/governance",
        signature="dGVzdF9rbXNfc2lnbmF0dXJl",
        propensity_score=0.92,
        causal_context={"graph_cycles": 1},
        requires_dual_approval=requires_dual,
        policy_tags=["FOUR_EYES_MANDATORY"],
    )


def _signed(token: ActionIntentToken, signer: LocalDevActionSigner) -> ActionIntentToken:
    """Sign a token exactly as the intent hub does, so the shelf can really verify it."""
    payload = {
        "intent_id": token.intent_id,
        "action_type": token.action_type,
        "parameters": token.parameters,
        "evidence_refs": token.evidence_refs,
        "severity": token.severity.value,
        "nonce": token.nonce,
        "issued_at": token.issued_at.isoformat(),
        "expires_at": token.expires_at.isoformat(),
        "requester_agent_id": token.requester_agent_id,
        "propensity_score": token.propensity_score,
        "causal_context": token.causal_context,
    }
    return token.model_copy(
        update={"signature": signer.sign_payload(payload), "kms_key_id": signer.key_id}
    )


def test_staged_token_card_contract_validation():
    signer = LocalDevActionSigner()
    shelf = GovernedActionShelf(signer=signer)
    token = _signed(_make_dummy_token(action_type="HoldWithdrawal"), signer)
    card = shelf.stage_token(token)

    contract_dict = card.to_contract_dict()
    assert validate_contract(contract_dict, "governed-action-card") is True
    assert contract_dict["action_type"] == "HoldWithdrawal"
    assert contract_dict["target_entity_id"] == "tx_99812"
    assert contract_dict["severity"] == "HIGH"
    assert contract_dict["requires_four_eyes"] is True
    assert contract_dict["kms_signature_verified"] is True
    assert contract_dict["status"] == "PENDING_APPROVAL"
    assert 0 <= contract_dict["seconds_remaining"] <= 900


def test_four_eyes_dual_approval_enforcement():
    shelf = GovernedActionShelf()
    token = _make_dummy_token(
        action_type="FreezeAccount", severity=ActionSeverity.HIGH, requires_dual=True
    )
    shelf.stage_token(token)

    # First approval by AML Investigator
    card_1 = shelf.submit_approval(
        intent_id=token.intent_id,
        approver_id="officer_alice_aml",
        approver_role="AML_INVESTIGATOR",
        comment="Suspicious rapid structuring confirmed.",
    )
    assert card_1.first_approver_id == "officer_alice_aml"
    assert card_1.second_approver_id is None
    # State remains PENDING_APPROVAL until second sign-off
    assert card_1.status == "PENDING_APPROVAL"

    # Attempt duplicate approval by Alice should fail
    with pytest.raises(ValueError, match="already approved"):
        shelf.submit_approval(
            intent_id=token.intent_id,
            approver_id="officer_alice_aml",
            approver_role="AML_INVESTIGATOR",
        )

    # Modal context check for Alice vs Bob
    alice_modal = shelf.get_approval_modal_context(
        token.intent_id, "officer_alice_aml", "AML_INVESTIGATOR"
    )
    assert alice_modal["can_approve"] is False
    assert "already signed" in alice_modal["ineligibility_reason"]

    bob_modal = shelf.get_approval_modal_context(
        token.intent_id, "officer_bob_head", "COMPLIANCE_HEAD"
    )
    assert bob_modal["can_approve"] is True

    # Second approval by distinct Compliance Head
    card_2 = shelf.submit_approval(
        intent_id=token.intent_id,
        approver_id="officer_bob_head",
        approver_role="COMPLIANCE_HEAD",
        comment="Executive freeze authorized.",
    )
    assert card_2.first_approver_id == "officer_alice_aml"
    assert card_2.second_approver_id == "officer_bob_head"
    assert card_2.status == "APPROVED"


def test_single_approver_fast_path():
    shelf = GovernedActionShelf()
    # Fast path: budget $1,200 <= $2,500, requires_dual=False
    now = datetime.now(UTC)
    token = ActionIntentToken(
        intent_id=str(uuid.uuid4()),
        action_type="LaunchRetentionPlaybook",
        parameters={
            "partner_id": "AP-1029",
            "budget": 1200.0,
            "playbook_id": "play_vip_spread_discount",
        },
        evidence_refs=["ev_churn_882"],
        severity=ActionSeverity.MEDIUM,
        status=ActionStatus.PENDING,
        nonce="nonce_fast_path",
        issued_at=now,
        expires_at=now + timedelta(seconds=900),
        requester_agent_id="PartnerAgent",
        kms_key_id="projects/eios/locations/global/keyRings/rings/cryptoKeys/governance",
        signature="dGVzdF9zaWc=",
        propensity_score=0.88,
        causal_context={},
        requires_dual_approval=False,
        policy_tags=["FAST_PATH_ELIGIBLE"],
    )
    shelf.stage_token(token)

    card = shelf.submit_approval(
        intent_id=token.intent_id,
        approver_id="officer_carol_partner",
        approver_role="PARTNER_MANAGER",
        comment="Fast-path retention budget deployed.",
    )
    # Immediately approved on single sign-off
    assert card.status == "APPROVED"
    assert card.first_approver_id == "officer_carol_partner"
    assert card.to_contract_dict()["action_type"] == "DeployRetentionVIPDeal"


def test_execution_state_transition():
    shelf = GovernedActionShelf()
    token = _make_dummy_token(action_type="HoldWithdrawal", requires_dual=False)
    shelf.stage_token(token)

    # Attempting to execute unapproved intent should fail
    with pytest.raises(ValueError, match="Cannot execute intent in status"):
        shelf.execute_action(token.intent_id)

    # Approve then execute
    shelf.submit_approval(token.intent_id, "officer_dave", "COMPLIANCE_HEAD")
    res = shelf.execute_action(token.intent_id)

    assert res["status"] == "COMMITTED"
    assert "receipt_id" in res
    assert shelf.present_card(shelf.get_token(token.intent_id)).status == "EXECUTED"


def test_token_expiration_transition():
    shelf = GovernedActionShelf()
    # Expired token (issued in past, expired)
    token = _make_dummy_token(expires_in_seconds=-10)
    shelf.stage_token(token)

    card = shelf.present_card(token)
    assert card.status == "EXPIRED"
    assert card.seconds_remaining == 0

    # Modal context shows ineligibility
    ctx = shelf.get_approval_modal_context(token.intent_id, "officer_eve", "AML_INVESTIGATOR")
    assert ctx["can_approve"] is False
    assert "expired" in ctx["ineligibility_reason"]


def test_unsigned_shelf_never_claims_a_verified_signature():
    shelf = GovernedActionShelf()
    card = shelf.stage_token(_make_dummy_token())
    assert card.kms_signature_verified is False
