"""Tests for Multi-Agent Supervisory Mesh Specialists, Router, and Action Execution Sink (T029, T030, T040)."""

import pytest
from langchain_core.messages import HumanMessage
from eios.conversation.router import SupervisoryRouter
from eios.conversation.models import SpecialistDomain
from eios.conversation.graph import ActionExecutionSink, BlackboardState
from eios.conversation.specialists.aml import SentinelAMLSpecialist
from eios.conversation.specialists.churn import ChurnRadarSpecialist
from eios.conversation.specialists.fraud import PartnerFraudSpecialist
from eios.conversation.specialists.governance import GovernanceAuditorSpecialist
from eios.conversation.specialists.synthesis import SynthesisSpecialist


def test_supervisory_router_all_domains():
    router = SupervisoryRouter()

    r1 = router.route_query("Please audit the action intent hash chain for Four-Eyes approval")
    assert r1.route == SpecialistDomain.GOVERNANCE
    assert r1.confidence > 0.9

    r2 = router.route_query("Investigate suspicious AML mule transaction structuring")
    assert r2.route == SpecialistDomain.SENTINEL_AML
    assert r2.confidence > 0.9

    r3 = router.route_query("Investigate affiliate partner fraud and collusion bonus abuse")
    assert r3.route == SpecialistDomain.PARTNER_FRAUD
    assert r3.confidence > 0.9

    r4 = router.route_query("Evaluate partner churn hazard and retention curve")
    assert r4.route == SpecialistDomain.CHURN_RADAR
    assert r4.confidence > 0.9

    r5 = router.route_query("Provide 4-horizon revenue forecast and briefing scenario")
    assert r5.route == SpecialistDomain.SYNTHESIS
    assert r5.confidence > 0.8

    r6 = router.route_query("General unrelated question")
    assert r6.route == SpecialistDomain.SYNTHESIS


def test_action_execution_sink_stages_cards():
    sink = ActionExecutionSink()
    assert len(sink.staged_cards) == 0

    card = sink.stage_action("SUSPEND_PARTNER", {"partner_id": "P-992"})
    assert card["type"] == "RecommendationCard"
    assert card["status"] == "STAGED_FOR_REVIEW"
    assert len(sink.staged_cards) == 1


def test_specialists_invoke_offline():
    aml = SentinelAMLSpecialist()
    assert "get_client_aml_dossier" in aml.allowed_tools
    state_aml = {
        "messages": [HumanMessage(content="Check client C-AML-ROUNDTRIP-01 for structuring")],
        "is_replay_fallback": True,
    }
    res_aml = aml.invoke(state_aml)
    assert len(res_aml.get("messages", [])) > 0

    churn = ChurnRadarSpecialist()
    state_churn = {
        "messages": [HumanMessage(content="Check partner AP-1029 churn risk")],
        "is_replay_fallback": True,
    }
    res_churn = churn.invoke(state_churn)
    assert len(res_churn.get("messages", [])) > 0

    fraud = PartnerFraudSpecialist()
    state_fraud = {
        "messages": [HumanMessage(content="Investigate partner P-992 collusion fraud")],
        "is_replay_fallback": True,
    }
    res_fraud = fraud.invoke(state_fraud)
    assert len(res_fraud.get("messages", [])) > 0

    gov = GovernanceAuditorSpecialist()
    state_gov = {
        "messages": [HumanMessage(content="Audit action intent act_992 ledger proof")],
        "is_replay_fallback": True,
    }
    res_gov = gov.invoke(state_gov)
    assert len(res_gov.get("messages", [])) > 0

    synth = SynthesisSpecialist()
    state_synth = {
        "messages": [HumanMessage(content="Synthesize executive morning briefing")],
        "is_replay_fallback": True,
    }
    res_synth = synth.invoke(state_synth)
    assert len(res_synth.get("messages", [])) > 0


def test_create_conversational_graph_compiles_and_runs():
    from unittest.mock import MagicMock
    from eios.ontology.auditor.gate import MetricAuditorGate
    from eios.conversation.graph import create_conversational_graph

    gateway = MagicMock()
    auditor = MetricAuditorGate(relative_tolerance=0.01)

    graph = create_conversational_graph(gateway, auditor)
    assert graph is not None

    state = {
        "messages": [HumanMessage(content="General query without keywords")],
        "reflection_cycles": 0,
        "extracted_evidence": [],
        "staged_actions": [],
        "next_agent": "supervisor",
        "final_response": "",
    }
    result = graph.invoke(state)
    assert "final_response" in result


def test_conversation_engine_facade():
    from unittest.mock import MagicMock
    from eios.conversation.engine import ConversationEngine
    from eios.conversation.models import ConversationQueryRequest
    from eios.ontology.auditor.gate import MetricAuditorGate

    gateway = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = "Forecast looks strong with 18 bps margin."
    gateway.complete.return_value = mock_resp
    auditor = MetricAuditorGate(relative_tolerance=0.01)
    engine = ConversationEngine(gateway, auditor)

    # 1. Speculative query refusal test
    req_spec = ConversationQueryRequest(
        user_query="Please make a speculative guess on future rates",
        session_id="sess_test_1"
    )
    res_spec = engine.query(req_spec)
    assert "cannot answer" in res_spec.response_markdown.lower()

    # 2. Regular query
    req_norm = ConversationQueryRequest(
        user_query="What is the forecast?",
        session_id="sess_test_2"
    )
    res_norm = engine.query(req_norm)
    assert res_norm.session_id == "sess_test_2"


