"""Tests for Copilot Engine Dual-Engine Grounding and Auditor Integration (F018, T010)."""

import pytest
from eios.conversation.copilot_engine import CopilotEngine
from eios.conversation.models import OperatorRole


@pytest.fixture
def copilot():
    return CopilotEngine(offline_mode=True)


def test_copilot_engine_executes_grounded_query_with_auditor_pass(copilot):
    """Verifies that grounded query runs tools and passes Metric Auditor Gate with zero unanchored numbers."""
    query = "What is the deposit turnover and churn risk for partner P-882?"
    res = copilot.process_query(query=query, role=OperatorRole.PARTNER_MANAGER)

    assert res.auditor_status == "PASS"
    assert "482,000" in res.response_markdown or "482000" in res.response_markdown
    assert len(res.provenance_citations) > 0
    assert any("net_deposit_volume_30d_usd" in c.citation_id for c in res.provenance_citations)


def test_copilot_engine_executes_aml_query_with_statutory_exemption(copilot):
    """Verifies AML inquiry invokes inspect_aml_entity and exempts legal citations."""
    query = "Investigate account CR84920 and cite the filing threshold"
    res = copilot.process_query(query=query, role=OperatorRole.AML_INVESTIGATOR)

    assert res.auditor_status == "PASS"
    assert "16" in res.response_markdown
    assert len(res.provenance_citations) > 0


def test_copilot_engine_executes_net_revenue_offline_query(copilot):
    """Verifies default executive synthesis offline branch for enterprise KPI."""
    query = "Provide current enterprise net revenue status"
    res = copilot.process_query(query=query, role=OperatorRole.EXECUTIVE)

    assert res.auditor_status == "PASS"
    assert "3,820,000" in res.response_markdown or "3820000" in res.response_markdown
    assert len(res.provenance_citations) > 0


def test_copilot_engine_live_mocked_execution():
    """Verifies live Gemini execution flow with tool function calling and auditor pass."""
    from unittest.mock import MagicMock
    from eios.conversation.client import GeminiClientManager

    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_client.chats.create.return_value = mock_chat

    # First response: function call to get_governed_metric
    fc = MagicMock()
    fc.name = "get_governed_metric"
    fc.args = {"metric_id": "net_revenue_usd"}

    resp1 = MagicMock()
    resp1.function_calls = [fc]
    resp1.text = None

    # Second response: final synthesis with anchored number
    resp2 = MagicMock()
    resp2.function_calls = []
    resp2.text = "Enterprise net revenue is anchored at $3,820,000 USD."

    mock_chat.send_message.side_effect = [resp1, resp2]

    client_mgr = GeminiClientManager(offline_mode=False)
    client_mgr._client = mock_client

    engine = CopilotEngine(client_manager=client_mgr)
    engine.is_offline_replay = False

    res = engine.process_query(query="Check net revenue", role=OperatorRole.EXECUTIVE)
    assert res.auditor_status == "PASS"
    assert "3,820,000" in res.response_markdown

