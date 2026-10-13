"""Integration tests for Canonical OMCP Governance Tools & Conversational Auditor Specialist (US6 / FR-013, FR-014, T034)."""

import pytest
from langchain_core.messages import HumanMessage

from eios.conversation.graph import create_conversational_graph
from eios.conversation.models import SpecialistDomain
from eios.conversation.router import SupervisoryRouter
from eios.conversation.specialists.governance import GovernanceAuditorSpecialist
from eios.ontology.omcp.server import OMCPServer


@pytest.fixture
def omcp_server(seeded_hot_state):
    return OMCPServer(hot_state=seeded_hot_state)


def test_omcp_governance_tool_propose_action(omcp_server):
    """Verify propose_action tool generates valid signed ActionIntentToken."""
    res = omcp_server.call_tool(
        "propose_action",
        {
            "action_type": "HoldWithdrawal",
            "parameters": {"txn_id": "TXN-OMCP-001", "reason": "SUSPICIOUS_VELOCITY"},
            "evidence_refs": ["EVID-AML-101"],
            "propensity_score": 0.88,
            "causal_context": {"baseline_loss": 5000.0},
        },
        caller_role="AMLInvestigator",
    )
    assert "intent_id" in res
    assert res["action_type"] == "HoldWithdrawal"
    assert res["severity"] == "HIGH"
    assert res["status"] == "PENDING"
    assert res["signature"] is not None
    assert res["propensity_score"] == 0.88


def test_omcp_governance_tool_approve_and_execute_flow(omcp_server):
    """Verify Four-Eyes dual approval and execution lifecycle through OMCP tools."""
    # 1. Propose High-severity action
    prop_res = omcp_server.call_tool(
        "propose_action",
        {
            "action_type": "HoldWithdrawal",
            "parameters": {"txn_id": "TXN-FLOW-001", "reason": "SANCTIONS_HOLD"},
            "evidence_refs": ["EVID-901"],
        },
        caller_role="SentinelAgent",
    )
    intent_id = prop_res["intent_id"]

    # 2. Check status
    status_1 = omcp_server.call_tool("get_intent_status", {"intent_id": intent_id})
    assert status_1["status"] == "PENDING"
    assert status_1["requires_dual_approval"] is True

    # 3. First approval (Officer 1)
    app_1 = omcp_server.call_tool(
        "approve_action",
        {
            "intent_id": intent_id,
            "approver_id": "officer_alice",
            "role": "ComplianceOfficer",
            "comment": "Verified sanctions match.",
        },
        caller_role="ComplianceOfficer",
    )
    assert app_1["status"] == "PENDING"
    assert app_1["approvals_count"] == 1

    # 4. Second approval (Officer 2 - Four-Eyes satisfied)
    app_2 = omcp_server.call_tool(
        "approve_action",
        {
            "intent_id": intent_id,
            "approver_id": "director_bob",
            "role": "ComplianceDirector",
            "comment": "Second sign-off confirmed.",
        },
        caller_role="ComplianceDirector",
    )
    assert app_2["status"] == "APPROVED"
    assert app_2["approvals_count"] == 2

    # 5. Execute action against simulated sink
    exec_res = omcp_server.call_tool(
        "execute_action",
        {"intent_id": intent_id, "idempotency_key": "IDEMP-FLOW-001"},
        caller_role="OperationsExecutive",
    )
    assert exec_res["status"] == "COMMITTED"
    assert "receipt_id" in exec_res
    assert exec_res["external_transaction_id"].startswith("SIM-CORE-TXN-")

    # 6. Re-executing with same idempotency key returns idempotent receipt
    exec_dup = omcp_server.call_tool(
        "execute_action",
        {"intent_id": intent_id, "idempotency_key": "IDEMP-FLOW-001"},
        caller_role="OperationsExecutive",
    )
    assert exec_dup["receipt_id"] == exec_res["receipt_id"]
    assert exec_dup["external_transaction_id"] == exec_res["external_transaction_id"]


def test_omcp_governance_tool_audit_and_hash_chain(omcp_server):
    """Verify get_ledger_audit_status and verify_hash_chain tools."""
    # Run audit check
    audit_res = omcp_server.call_tool(
        "get_ledger_audit_status", {}, caller_role="ComplianceAuditor"
    )
    assert audit_res["is_valid"] is True
    assert audit_res["integrity_score"] == 1.0
    assert audit_res["head_seq"] >= 0
    assert audit_res["tampered_sequence_id"] is None

    # Run verify_hash_chain tool
    chain_res = omcp_server.call_tool("verify_hash_chain", {}, caller_role="ComplianceAuditor")
    assert chain_res["is_valid"] is True
    assert chain_res["integrity_score"] == 1.0


def test_governance_auditor_specialist_live_and_replay(omcp_server):
    """Verify GovernanceAuditorSpecialist live OMCP resolution and deterministic [REPLAY] fallback."""
    specialist = GovernanceAuditorSpecialist(omcp_server=omcp_server)
    assert specialist.domain == SpecialistDomain.GOVERNANCE
    assert "get_ledger_audit_status" in specialist.allowed_tools

    # Live query resolution
    live_res = specialist.handle_query("What is the current health of the action ledger?")
    assert live_res["is_fallback"] is False
    assert "Cryptographic Ledger Audit Report: Status=HEALTHY" in live_res["content"]
    assert "Integrity Score: 100.0%" in live_res["content"]
    assert "Four-Eyes" in live_res["content"]

    # Simulated LLM outage replay fallback
    replay_res = specialist.handle_query("What is the audit status?", simulate_llm_outage=True)
    assert replay_res["is_fallback"] is True
    assert "[REPLAY]" in replay_res["content"]
    assert "Integrity score: 1.00 (100%)" in replay_res["content"]


def test_supervisory_router_routing():
    """Verify SupervisoryRouter routes governance queries to GOVERNANCE domain."""
    router = SupervisoryRouter()

    dec_1 = router.route_query("Please audit the ledger hash chain for tampering")
    assert dec_1.route == SpecialistDomain.GOVERNANCE
    assert dec_1.confidence >= 0.95

    dec_2 = router.route_query("Check Four-Eyes approvals on action intent #42")
    assert dec_2.route == SpecialistDomain.GOVERNANCE

    dec_3 = router.route_query("Investigate mule syndicate laundering")
    assert dec_3.route == SpecialistDomain.SENTINEL_AML


def test_langgraph_governance_node_execution(omcp_server):
    """Verify conversational LangGraph supervisor routes and executes governance node."""
    from unittest.mock import MagicMock

    gateway = MagicMock()
    auditor = MagicMock()
    graph = create_conversational_graph(gateway=gateway, auditor=auditor)

    initial_state = {
        "messages": [HumanMessage(content="Show me the action ledger audit status")],
        "next_agent": "supervisor",
        "reflection_cycles": 0,
        "extracted_evidence": [],
        "staged_actions": [],
        "final_response": "",
        "omcp_server": omcp_server,
    }

    result = graph.invoke(initial_state)
    assert result["reflection_cycles"] >= 1
    assert "final_response" in result
    assert "Ledger" in result["final_response"] or "Cryptographic" in result["final_response"]
