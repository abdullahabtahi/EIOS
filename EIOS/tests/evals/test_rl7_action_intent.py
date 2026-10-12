"""Tests for RL-7: Governed Action Intent Verification (T018)."""

from datetime import UTC, datetime, timedelta

import pytest

from evals.suites.redlines.test_rl7_action_intent import (
    FourEyesApprovalRequiredError,
    InvalidSignatureError,
    NonceReplayError,
    TokenExpiredError,
    create_test_action_token,
    verify_action_intent_token,
)


def test_rl7_valid_token_passes():
    token = create_test_action_token(
        action_type="FLAG_SAR",
        entity_id="tok_usr_100",
        severity="low",
    )
    result = verify_action_intent_token(token)
    assert result.passed is True
    assert result.violations_detected == 0


def test_rl7_invalid_signature_fails():
    token = create_test_action_token(action_type="FREEZE_ACCOUNT")
    token["signature"] = "corrupted_signature_hex"
    with pytest.raises(InvalidSignatureError):
        verify_action_intent_token(token)


def test_rl7_expired_token_fails():
    token = create_test_action_token(expires_at=datetime.now(UTC) - timedelta(minutes=10))
    with pytest.raises(TokenExpiredError):
        verify_action_intent_token(token)


def test_rl7_nonce_replay_fails():
    token = create_test_action_token(nonce="unique_nonce_12345")
    # First verification passes
    res1 = verify_action_intent_token(token)
    assert res1.passed is True

    # Replay with same nonce must raise NonceReplayError
    with pytest.raises(NonceReplayError):
        verify_action_intent_token(token)


def test_rl7_high_severity_requires_four_eyes():
    token = create_test_action_token(
        action_type="FREEZE_ACCOUNT",
        severity="high",
        signatures=["sig_officer_1"],  # Only 1 approval provided
    )
    with pytest.raises(FourEyesApprovalRequiredError):
        verify_action_intent_token(token)
