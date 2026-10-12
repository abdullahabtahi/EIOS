"""Test the 13 canonical OMCP tool implementations (contracts/omcp-tools.json, T043)."""

import pytest

from eios.ontology.omcp.server import OMCPServer


@pytest.fixture
def omcp_server(seeded_hot_state):
    return OMCPServer(hot_state=seeded_hot_state)


def test_tool_get_metric(omcp_server):
    res = omcp_server.call_tool(
        "get_metric",
        {"metric_id": "net_deposit_volume_usd", "filters": {"currency": "USD"}},
    )
    assert res["metric_id"] == "net_deposit_volume_usd"
    assert "value" in res
    assert res["unit"] == "USD"
    assert "definition_version" in res


def test_tool_list_metrics(omcp_server):
    res = omcp_server.call_tool("list_metrics", {})
    assert "metrics" in res
    assert len(res["metrics"]) >= 10


def test_tool_get_entity(omcp_server):
    res = omcp_server.call_tool(
        "get_entity",
        {"type": "ClientAccount", "id": "C-1001"},
        caller_role="AMLInvestigator",
    )
    assert res["id"] == "C-1001"
    assert res["type"] == "ClientAccount"
    assert "properties" in res


def test_tool_traverse_graph(omcp_server):
    res = omcp_server.call_tool(
        "traverse_graph",
        {"seed_ids": ["C-1001"], "hops": 2, "suppress_hubs": True},
    )
    assert "nodes" in res
    assert "edges" in res
    assert "hub_flags" in res


def test_tool_propose_action_and_get_status(omcp_server):
    res = omcp_server.call_tool(
        "propose_action",
        {
            "action_type": "HoldWithdrawal",
            "parameters": {"txn_id": "TXN-1", "reason": "HIGH_VELOCITY"},
            "evidence_refs": ["EVID-101"],
        },
    )
    assert "intent_id" in res
    assert res["status"] == "PENDING"
    assert res["signature"] is not None

    status_res = omcp_server.call_tool("get_intent_status", {"intent_id": res["intent_id"]})
    assert status_res["status"] == "PENDING"


def test_tool_get_partner_signals(omcp_server):
    res = omcp_server.call_tool("get_partner_signals", {"partner_id": "P-101"})
    assert res["partner_id"] == "P-101"
    assert "signals" in res
    assert "churn_hazard_score" in res


def test_tool_get_ring_evidence(omcp_server):
    res = omcp_server.call_tool("get_ring_evidence", {"ring_id": "RING-01"})
    assert res["ring_id"] == "RING-01"
    assert "members" in res
    assert "timing_stats" in res


def test_tool_get_causal_chain(omcp_server):
    res = omcp_server.call_tool("get_causal_chain", {"outcome_metric": "net_deposit_volume_usd"})
    assert res["outcome_metric"] == "net_deposit_volume_usd"
    assert "edges" in res
    assert res["gate_verdict"] in ["PASS", "FAIL"]


def test_tool_run_scenario(omcp_server):
    res = omcp_server.call_tool(
        "run_scenario",
        {"shock_spec": {"competitor_payout_rate": 0.05}},
    )
    assert "propagated_deltas" in res
    assert "confidence_intervals" in res


def test_tool_get_forecast(omcp_server):
    res = omcp_server.call_tool("get_forecast", {"metric_id": "net_deposit_volume_usd"})
    assert res["metric_id"] == "net_deposit_volume_usd"
    assert "point_estimate" in res
    assert "driver_attribution" in res
    # Driver attribution must sum to 100%
    total_attrib = sum(res["driver_attribution"].values())
    assert abs(total_attrib - 100.0) < 0.01


def test_tool_get_briefing(omcp_server):
    res = omcp_server.call_tool("get_briefing", {"date": "2026-10-05"})
    assert "briefing_id" in res
    assert "insights" in res
    assert "risks" in res
    assert "opportunities" in res


def test_tool_search_comms(omcp_server):
    res = omcp_server.call_tool("search_comms", {"partner_id": "P-101", "query": "commission"})
    assert res["partner_id"] == "P-101"
    assert "passages" in res
