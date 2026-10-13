"""The copilot may only PROPOSE an action; signing and staging belong to the intent hub (Principle II, T021)."""

from eios.conversation.tools import stage_action_intent


def test_stage_action_intent_only_proposes_and_never_claims_a_signature():
    proposal = stage_action_intent(
        action_type="HoldWithdrawal",
        target_entity_id="CR84920",
        reason="Discrepancy multiplier 16x observed on velocity spike",
    )
    assert proposal["action_type"] == "HoldWithdrawal"
    assert proposal["target_entity_id"] == "CR84920"
    assert proposal["status"] == "PROPOSED"
    assert proposal["signed"] is False
    assert proposal["requires_four_eyes"] is True
    # No fabricated cryptographic material: only the intent hub can mint these.
    for forged_field in ("signature", "kms_key_id", "nonce", "intent_id", "expires_at"):
        assert forged_field not in proposal


def test_proposals_are_unique():
    first = stage_action_intent(action_type="HoldWithdrawal", target_entity_id="CR84920")
    second = stage_action_intent(action_type="HoldWithdrawal", target_entity_id="CR84920")
    assert first["proposal_id"] != second["proposal_id"]
