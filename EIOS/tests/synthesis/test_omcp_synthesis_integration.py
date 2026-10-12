"""Integration tests for OMCP synthesis tool dispatch handlers (T032, US6)."""

import time

import pytest

from eios.ontology.omcp.server import OMCPServer


@pytest.fixture
def server(seeded_hot_state):
    """Instantiate OMCPServer backed by seeded DuckDB hot state."""
    return OMCPServer(hot_state=seeded_hot_state)


def test_omcp_get_causal_chain_dispatch(server):
    """Verify get_causal_chain dispatches to synthesis SCM and satisfies latency target (< 100ms)."""
    t0 = time.perf_counter()
    res = server.call_tool("get_causal_chain", {"outcome_metric": "net_deposit_volume_usd"})
    duration_ms = (time.perf_counter() - t0) * 1000.0

    assert duration_ms < 100.0, f"Latency {duration_ms:.2f}ms exceeded 100ms target"
    assert res["outcome_metric"] == "net_deposit_volume_usd"
    assert "edges" in res
    assert len(res["edges"]) >= 1
    assert res["gate_verdict"] in ["PASS", "FAIL"]
    assert "model_version" in res


def test_omcp_run_scenario_dispatch(server):
    """Verify run_scenario dispatches to ScenarioSimulator and returns bounded confidence intervals."""
    t0 = time.perf_counter()
    res = server.call_tool(
        "run_scenario",
        {"shock_spec": {"competitor_payout_rate": 0.05}},
    )
    duration_ms = (time.perf_counter() - t0) * 1000.0

    assert duration_ms < 200.0, f"Latency {duration_ms:.2f}ms exceeded 200ms target"
    assert "propagated_deltas" in res
    assert "confidence_intervals" in res
    assert "assumptions" in res
    assert "partner_churn_rate" in res["propagated_deltas"]


def test_omcp_get_forecast_dispatch(server):
    """Verify get_forecast dispatches and returns 100% additive driver attribution."""
    res = server.call_tool("get_forecast", {"metric_id": "net_deposit_volume_usd"})

    assert res["metric_id"] == "net_deposit_volume_usd"
    assert "point_estimate" in res
    assert "ci_lower" in res
    assert "ci_upper" in res
    assert "driver_attribution" in res

    attrib = res["driver_attribution"]
    assert len(attrib) >= 1
    total_pct = sum(attrib.values())
    assert abs(total_pct - 100.0) < 0.001, f"Attribution sum {total_pct} != 100.0%"


def test_omcp_get_briefing_dispatch(server):
    """Verify get_briefing dispatches to MorningBriefingGenerator with >=3 insights, >=2 risks, >=1 opp."""
    res = server.call_tool("get_briefing", {"date": "2026-10-06"})

    assert res["briefing_id"].startswith("BRIEF-")
    assert len(res["insights"]) >= 3
    assert len(res["risks"]) >= 2
    assert len(res["opportunities"]) >= 1


def test_omcp_propose_action_with_aipw_logging(server):
    """Verify propose_action captures propensity score and causal context without executing mutations."""
    res = server.call_tool(
        "propose_action",
        {
            "action_type": "AdjustPartnerTier",
            "parameters": {"partner_id": "P-101", "target_tier": "TIER_1"},
            "evidence_refs": ["EVID-CAUSAL-01"],
            "propensity_score": 0.85,
            "causal_context": {"partner_churn_rate": 0.18, "tenure_months": 24.0},
        },
    )

    assert "intent_id" in res
    assert res["status"] == "PENDING"
    assert res["propensity_score"] == 0.85
    assert res["causal_context"]["partner_churn_rate"] == 0.18
    assert res["signature"] is not None
