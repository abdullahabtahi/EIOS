"""Tests for 2PC ActionIntentToken staging and Four-Eyes governance (Principle II, T021)."""

from eios.conversation.tools import stage_action_intent


def test_stage_action_intent_produces_signed_governed_token():
    token_dict = stage_action_intent(
        action_type="HoldWithdrawal",
        target_entity_id="CR84920",
        reason="Discrepancy multiplier 16x observed on velocity spike",
    )
    assert "intent_id" in token_dict
    assert token_dict["action_type"] == "HoldWithdrawal"
    assert token_dict["target_entity_id"] == "CR84920"
    assert token_dict["status"] == "STAGED_FOR_REVIEW"
    assert token_dict["requires_four_eyes"] is True
    assert "signature" in token_dict
    assert "nonce" in token_dict
