"""Test deterministic server-side ontology functions (T027)."""

import time

from eios.ontology.core.objects import ClientAccount, Partner
from eios.ontology.functions.fraud import client_quality_score, ring_membership
from eios.ontology.functions.partner import churn_priority, partner_value_at_risk
from eios.ontology.functions.scenario import scenario_propagate


def test_partner_value_at_risk_and_churn_priority():
    partner = Partner(
        partner_id="P-101",
        tier="TIER_1",
        tenure_days=720,
        value_at_risk_usd=120000.0,
    )
    var = partner_value_at_risk(partner, hazard_score=0.35)
    assert var == 42000.0  # 120000 * 0.35

    prio = churn_priority(partner, disengage_prob=0.80)
    assert prio["priority_tier"] == "CRITICAL"
    assert prio["score"] > 0.7


def test_client_quality_score_deterministic():
    client = ClientAccount(
        client_id="C-1001",
        kyc_status="APPROVED",
        segment="VIP",
        lifetime_value_usd=25000.0,
    )
    score = client_quality_score(client, deposit_withdrawal_ratio=2.2, chargeback_count=0)
    assert 0.0 <= score <= 1.0
    assert score > 0.8  # High value VIP client with zero chargebacks


def test_ring_membership_scoring():
    members = ["C-1011", "C-1012", "C-1013"]
    shared_attrs = ["DEV-RING-1", "IP-RING-1"]
    ring_score = ring_membership(members=members, shared_attrs=shared_attrs, turnover_symmetry=0.95)

    assert 0.0 <= ring_score["severity_score"] <= 1.0
    assert ring_score["severity_score"] >= 0.85
    assert ring_score["member_count"] == 3


def test_scenario_propagate_parametric_shock():
    shock_spec = {"competitor_payout_rate": 0.05}  # +5% competitor commission bump
    causal_edges = [
        {"from": "competitor_payout_rate", "to": "top_partner_mix", "weight": -0.60},
        {"from": "top_partner_mix", "to": "new_client_quality", "weight": 0.75},
        {"from": "new_client_quality", "to": "net_deposit_volume_usd", "weight": 0.80},
    ]
    deltas = scenario_propagate(shock_spec=shock_spec, causal_edges=causal_edges)

    assert "top_partner_mix" in deltas
    assert deltas["top_partner_mix"] == -0.03  # 0.05 * -0.60
    assert "new_client_quality" in deltas
    assert "net_deposit_volume_usd" in deltas
    assert deltas["net_deposit_volume_usd"] < 0.0  # Net deposit volume drops


def test_deterministic_functions_sub_5ms_latency():
    partner = Partner(partner_id="P-99", tier="TIER_2", value_at_risk_usd=50000.0)
    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        _ = partner_value_at_risk(partner, hazard_score=0.25)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    assert p95 < 5.0, f"Function execution exceeded 5ms: {p95:.2f}ms"
