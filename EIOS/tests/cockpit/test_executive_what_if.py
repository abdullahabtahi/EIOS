"""Tests for Executive Decision Cockpit: Morning Briefing, Causal DAG, and What-If Shock."""

import time

import pytest

from eios.cockpit.executive import ExecutiveCockpitService
from eios.cockpit.schemas import validate_contract


def test_morning_briefing_contract():
    svc = ExecutiveCockpitService()
    briefing = svc.get_morning_briefing()

    assert len(briefing.horizons) == 4
    horizon_names = [h.horizon_name for h in briefing.horizons]
    assert horizon_names == ["Competitive", "Partner", "Client", "Financial"]
    assert len(briefing.risks) >= 1
    assert len(briefing.opportunities) >= 1

    contract_dict = briefing.to_contract_dict()
    assert validate_contract(contract_dict, "morning-briefing-dossier") is True


def test_causal_dag_contract_and_refuters():
    svc = ExecutiveCockpitService()
    dag = svc.get_causal_dag()

    assert len(dag.nodes) == 4
    assert len(dag.edges) >= 3

    # Verify that causal gate passes on verified edge
    verified_edge = next(
        e
        for e in dag.edges
        if e.source_node_id == "competitor_payout_rate" and e.target_node_id == "partner_churn_rate"
    )
    assert verified_edge.refuter.is_causal_verified is True
    assert verified_edge.refuter.confidence >= 0.80
    assert verified_edge.refuter.status_label == "Verified Causal"

    # Verify unverified edge is labelled correlation only
    unverified_edge = next(
        e
        for e in dag.edges
        if e.target_node_id == "net_pnl_usd" and e.source_node_id == "competitor_payout_rate"
    )
    assert unverified_edge.refuter.is_causal_verified is False
    assert "Correlation Detected" in unverified_edge.refuter.status_label

    contract_dict = dag.to_contract_dict()
    assert validate_contract(contract_dict, "causal-dag-graph") is True


def test_what_if_shock_sub_200ms_latency_and_100_percent_attribution():
    svc = ExecutiveCockpitService()

    t0 = time.perf_counter()
    res = svc.simulate_what_if_shock(shock_param="competitor_payout_spread", magnitude_pct=15.0)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Sub-200ms target latency SLA
    assert elapsed_ms < 200.0

    # Attribution sum must equal exactly 100%
    assert res["attribution_sum_pct"] == pytest.approx(100.0, abs=0.01)

    # Directional correctness
    assert res["projected_changes"]["partner_churn_delta_pct"] > 0
    assert res["projected_changes"]["projected_ebitda_impact_usd"] < 0
