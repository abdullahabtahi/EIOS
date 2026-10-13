"""Tests for conversational agent data models and serialization (F018, T004)."""

from datetime import UTC, datetime

import pytest

from eios.conversation.models import (
    ActionIntentToken,
    ActionSeverity,
    ActionStatus,
    BlackboardState,
    ConversationSession,
    OperatorRole,
    SpecialistRoute,
    sanitize_for_state_storage,
)


def test_conversation_session_validation():
    session = ConversationSession(
        session_id="sess_101",
        thread_id="th_101",
        operator_id="op_admin",
        operator_role=OperatorRole.AML_INVESTIGATOR,
        active_entity_anchor="CR84920",
    )
    assert session.session_id == "sess_101"
    assert session.active_entity_anchor == "CR84920"
    assert session.turn_count == 0


def test_blackboard_state_reflection_bounded():
    state = BlackboardState(
        next_agent="supervisor",
        active_route=SpecialistRoute.AML_INVESTIGATOR,
        reflection_cycles=2,
    )
    assert state.reflection_cycles == 2

    with pytest.raises(Exception):  # noqa: B017
        # Reflection cycles hard capped at 3
        BlackboardState(reflection_cycles=4)


def test_action_intent_token_governance():
    token = ActionIntentToken(
        intent_id="act_991",
        action_type="HoldWithdrawal",
        target_entity_id="CR84920",
        parameters={"amount": 8000.0, "currency": "USD"},
        evidence_refs=["ev_turnover_16x"],
        severity=ActionSeverity.HIGH,
        status=ActionStatus.STAGED_FOR_REVIEW,
        nonce="nonce_abc123",
        expires_at=datetime.now(UTC),
        requester_agent_id="agent_aml_sentinel",
        kms_key_id="projects/spatial-cat-489006-a4/locations/us-central1/keyRings/gov/cryptoKeys/p256",
        signature="MEYCIQDf...",
    )
    assert token.requires_four_eyes is True
    assert token.status == ActionStatus.STAGED_FOR_REVIEW


def test_sanitize_for_state_storage_strips_numpy_and_truncates():
    """Validates pre-mortem countermeasure against Firestore 1MB blowout."""
    import numpy as np

    raw_payload = {
        "large_array": np.array([1.0, 2.0, 3.0]),
        "numpy_int": np.int64(42),
        "nested": {"val": np.float64(3.14)},
    }
    sanitized = sanitize_for_state_storage(raw_payload)
    assert isinstance(sanitized["numpy_int"], int)
    assert sanitized["numpy_int"] == 42
    assert isinstance(sanitized["large_array"], list)
    assert sanitized["nested"]["val"] == 3.14


def test_copilot_tracer():
    from eios.conversation.telemetry import CopilotTracer

    tracer = CopilotTracer()
    with tracer.trace_turn("sess_trace_1", 1, "test query", "executive") as meta:
        assert meta["session_id"] == "sess_trace_1"
        assert meta["role"] == "executive"
        meta["auditor_status"] = "PASS"

    assert "duration_ms" in meta
    assert meta["auditor_status"] == "PASS"
