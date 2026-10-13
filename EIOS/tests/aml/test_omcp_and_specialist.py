"""Unit and integration tests for AML OMCP tools and SentinelAMLSpecialist (T041, T042).

Authoritative References:
- specs/010-client-aml/spec.md (User Story 6, SC-006, SC-007)
- .specify/memory/constitution.md (Principles I, II, VII, VIII)
"""

from langchain_core.messages import HumanMessage

from eios.conversation.specialists.aml import SentinelAMLSpecialist
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.omcp.server import OMCPServer


def test_omcp_aml_tool_handlers() -> None:
    """Verify all 6 canonical AML OMCP tool handlers execute and adhere to contracts."""
    hot_state = HotStateEngine()
    server = OMCPServer(hot_state=hot_state)

    # 1. get_client_aml_dossier
    dossier = server.call_tool(
        "get_client_aml_dossier",
        {"client_id": "C-AML-TEST-01"},
        caller_role="ComplianceOfficer",
    )
    assert dossier["client_id"] == "C-AML-TEST-01"
    assert "narrative_summary" in dossier
    assert "composite_risk_score" in dossier

    # 2. get_mule_ring_graph
    mule_graph = server.call_tool(
        "get_mule_ring_graph",
        {"client_id": "C-AML-TEST-01"},
        caller_role="ComplianceOfficer",
    )
    assert "cluster_id" in mule_graph
    assert "plain_language_explanation" in mule_graph
    assert isinstance(mule_graph["member_client_ids"], list)

    # 3. get_roundtrip_structuring_alerts
    alerts = server.call_tool(
        "get_roundtrip_structuring_alerts",
        {"client_id": "C-AML-TEST-01"},
        caller_role="ComplianceOfficer",
    )
    assert "alerts" in alerts
    assert "total_detected" in alerts
    assert alerts["window_hours"] == 72.0

    # 4. check_withdrawal_risk
    withdrawal_assessment = server.call_tool(
        "check_withdrawal_risk",
        {
            "withdrawal_id": "W-TEST-001",
            "client_id": "C-AML-TEST-01",
            "amount_usd": 5000.0,
        },
        caller_role="SentinelAgent",
    )
    assert withdrawal_assessment["withdrawal_id"] == "W-TEST-001"
    assert withdrawal_assessment["recommendation"] in ["ALLOW", "PROPOSE_HOLD", "PROPOSE_FREEZE"]
    assert withdrawal_assessment["decision_latency_ms"] >= 0.0

    # 5. generate_sar_draft
    sar_draft = server.call_tool(
        "generate_sar_draft",
        {"client_id": "C-AML-TEST-01", "jurisdiction": "US_FINCEN"},
        caller_role="ComplianceOfficer",
    )
    assert sar_draft["client_id"] == "C-AML-TEST-01"
    assert sar_draft["jurisdiction"] == "US_FINCEN"
    assert len(sar_draft["statutory_provisions"]) >= 1

    # 6. propose_aml_action
    action = server.call_tool(
        "propose_aml_action",
        {
            "action_type": "HoldWithdrawal",
            "parameters": {"withdrawal_id": "W-TEST-001", "amount": 5000.0},
            "evidence_refs": ["DP1:transactions_aml/C-AML-TEST-01"],
        },
        caller_role="ComplianceOfficer",
    )
    assert action["action_type"] == "HoldWithdrawal"
    assert action["status"] == "PENDING"
    assert len(action["signature"]) > 0


def test_sentinel_aml_specialist_with_server() -> None:
    """Verify SentinelAMLSpecialist grounds reasoning in OMCP server output."""
    hot_state = HotStateEngine()
    server = OMCPServer(hot_state=hot_state)
    specialist = SentinelAMLSpecialist(omcp_server=server)

    state = {
        "messages": [
            HumanMessage(content="Assess account C-AML-ROUNDTRIP-01 for laundering risk.")
        ],
        "reflection_cycles": 0,
    }

    result = specialist.invoke(state)
    assert len(result["messages"]) == 1
    content = result["messages"][0].content
    assert "C-AML-ROUNDTRIP-01" in content
    assert "Composite AML risk score" in content
    assert result["next_agent"] == "supervisor"
    assert result["reflection_cycles"] == 1


def test_sentinel_aml_specialist_replay_fallback() -> None:
    """Verify SentinelAMLSpecialist emits [REPLAY] badge under server outage (Principle VIII)."""
    specialist = SentinelAMLSpecialist(omcp_server=None)

    state = {
        "messages": [HumanMessage(content="Check withdrawal risk for C-AML-999.")],
        "reflection_cycles": 0,
    }

    result = specialist.invoke(state)
    assert len(result["messages"]) == 1
    content = result["messages"][0].content
    assert "[REPLAY]" in content
    assert "31 CFR 1010" in content
    assert result["extracted_evidence"][0]["is_replay"] is True
