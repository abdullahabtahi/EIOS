"""Tests for persistent session checkpointer and state rehydration (F018, T017)."""

import pytest
from eios.conversation.checkpointer import ThreadCheckpointer
from eios.conversation.models import OperatorRole


def test_thread_checkpointer_saves_and_rehydrates(tmp_path):
    db_path = str(tmp_path / "checkpoints.db")
    cp = ThreadCheckpointer(db_path=db_path)

    # Save turn state
    state_payload = {
        "session_id": "sess_chk_1",
        "thread_id": "th_1",
        "operator_role": "aml_investigator",
        "active_anchor": "CR84920",
        "turn_count": 2,
    }
    cp.save_state(thread_id="th_1", state=state_payload)

    # Rehydrate
    rehydrated = cp.get_state(thread_id="th_1")
    assert rehydrated is not None
    assert rehydrated["active_anchor"] == "CR84920"
    assert rehydrated["turn_count"] == 2


def test_thread_checkpointer_handles_missing_thread(tmp_path):
    db_path = str(tmp_path / "checkpoints.db")
    cp = ThreadCheckpointer(db_path=db_path)
    res = cp.get_state(thread_id="th_nonexistent")
    assert res is None
