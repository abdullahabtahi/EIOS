"""Tests for EIOS Live Backend API Routes and Native SSE Streaming (F019 Phase 2)."""

import pytest
from fastapi.testclient import TestClient

from eios.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "UP"
    assert data["sse_enabled"] is True


def test_churn_radar_and_cohorts(client):
    res = client.get("/api/v1/churn/radar")
    assert res.status_code == 200
    data = res.json()
    assert "partners" in data
    assert "aggregate_var_30d_usd" in data
    assert len(data["partners"]) >= 3

    res_cohorts = client.get("/api/v1/churn/cohorts")
    assert res_cohorts.status_code == 200
    cohort_data = res_cohorts.json()
    assert "cohorts" in cohort_data
    assert len(cohort_data["cohorts"]) >= 2


def test_fraud_tree_and_pairs(client):
    res = client.get("/api/v1/fraud/tree?partner_id=AP-1029")
    assert res.status_code == 200
    data = res.json()
    assert data["master_partner_id"] == "AP-1029"
    assert "total_clawback_exposure_usd" in data

    res_pairs = client.get("/api/v1/fraud/pairs")
    assert res_pairs.status_code == 200
    pair_data = res_pairs.json()
    assert "active_collusion_rings" in pair_data


def test_aml_triage_dossier_and_graph(client):
    res_triage = client.get("/api/v1/aml/triage")
    assert res_triage.status_code == 200
    triage = res_triage.json()
    assert "alerts" in triage
    assert len(triage["alerts"]) >= 1

    res_dossier = client.get("/api/v1/aml/dossier/case_aml_84920")
    assert res_dossier.status_code == 200
    dossier = res_dossier.json()
    assert dossier["entity_id"] == "84920"
    assert "sar_draft" in dossier
    assert "peer_group_comparison" in dossier

    res_graph = client.get("/api/v1/aml/dossier/case_aml_84920/graph")
    assert res_graph.status_code == 200
    graph = res_graph.json()
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) > 20  # Mule nodes generated


def test_synthesis_what_if_and_briefing(client):
    res_what_if = client.post(
        "/api/v1/synthesis/what-if",
        json={"shock_param": "competitor_commission_bps", "magnitude_pct": 25.0},
    )
    assert res_what_if.status_code == 200
    sim_data = res_what_if.json()
    assert "attribution_waterfall" in sim_data
    assert 99.98 <= sim_data["attribution_sum_pct"] <= 100.02

    res_briefing = client.get("/api/v1/synthesis/briefing")
    assert res_briefing.status_code == 200
    briefing = res_briefing.json()
    assert "horizons" in briefing

    res_dag = client.get("/api/v1/synthesis/dag")
    assert res_dag.status_code == 200
    dag = res_dag.json()
    assert "nodes" in dag


def test_sse_churn_stream(client):
    res = client.get("/api/v1/churn/stream")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]


def test_partner_ontology_and_genai_battlecards(client):
    # Test Palantir Foundry Object 360 Endpoint
    res_ont = client.get("/api/v1/churn/partner/AP-1029/ontology")
    assert res_ont.status_code == 200
    ont_data = res_ont.json()
    assert ont_data["object_type"] == "Partner"
    assert ont_data["primary_key"] == "AP-1029"
    assert len(ont_data["links"]) >= 4
    assert ont_data["properties"]["value_at_risk_usd"] == 540000.0

    # Test Gemini Battlecards
    res_cards = client.get("/api/v1/churn/partner/AP-1029/battlecards")
    assert res_cards.status_code == 200
    card_data = res_cards.json()
    assert card_data["synthesizer_model"] is not None
    assert len(card_data["battlecards"]) == 3
    assert "forensic_diagnostic_narrative" in card_data

    # Test Gemini What-If Simulator
    res_what_if = client.post(
        "/api/v1/churn/partner/AP-1029/what-if",
        json={"proposal_prompt": "What if I offer 50% rev-share bump?"},
    )
    assert res_what_if.status_code == 200
    sim_data = res_what_if.json()
    assert sim_data["evaluator_model"] is not None
    assert sim_data["projected_retention_lift_pct"] == 82.0
    assert sim_data["causal_refuter_p_value"] > 0.05
