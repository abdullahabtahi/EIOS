"""Tests for honest refusal and ungrounded query boundaries (Principle III, T011)."""

import pytest
from eios.conversation.copilot_engine import CopilotEngine
from eios.conversation.models import OperatorRole


def test_copilot_engine_refuses_speculative_out_of_domain_queries():
    copilot = CopilotEngine(offline_mode=True)
    speculative_query = "What will competitor Apex Global's net profit be in 2030?"
    res = copilot.process_query(query=speculative_query, role=OperatorRole.EXECUTIVE)

    assert "insufficient data" in res.response_markdown.lower()
    assert res.auditor_status == "BLOCKED"


def test_copilot_engine_refuses_guesses_without_data():
    copilot = CopilotEngine(offline_mode=True)
    query = "Guess how many unrecorded transactions occurred without any logging"
    res = copilot.process_query(query=query, role=OperatorRole.EXECUTIVE)

    assert "insufficient data" in res.response_markdown.lower()
