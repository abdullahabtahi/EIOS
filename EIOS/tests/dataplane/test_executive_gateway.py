"""The gateway serves the executive screen from the engine service and says so (spec 034 FR-006 to FR-009)."""

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import server
from eios.cockpit.server import ENGINE_DATA_BADGE, app
from eios.dataplane.executive_service import EngineExecutiveService


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, executive_service: EngineExecutiveService
) -> TestClient:
    monkeypatch.setattr(server, "executive_svc", executive_service)
    monkeypatch.setattr(server, "executive_engine_service", lambda: executive_service)
    return TestClient(app)


def test_the_executive_workstation_is_computed_and_badged_as_engine(client: TestClient) -> None:
    body = client.get("/api/cockpit/workstations/executive").json()
    assert body["fallback_state"]["badge_label"] == ENGINE_DATA_BADGE
    titles = " ".join(i["title"] + i["subtitle"] for i in body["triage_queue"]["items"])
    assert "Spread Shock LatAm" not in titles and "18 bps" not in titles
    sections = {s["section_id"]: s for s in body["active_dossier"]["sections"]}
    assert set(sections) == {"sec_competitive", "sec_partner", "sec_client", "sec_financial"}
    payout = sections["sec_competitive"]["metrics"][0]
    assert payout["formatted_value"].startswith("0.") and "%" not in payout["formatted_value"]
    assert {n["node_id"] for n in body["kinetic_canvas"]["payload"]["nodes"]} >= {
        "competitor_payout_rate",
        "net_revenue_usd",
    }


def test_the_board_carries_briefing_forecast_graph_and_shocks(client: TestClient) -> None:
    body = client.get("/api/cockpit/executive").json()
    assert body["data_origin"] == "engine"
    assert len(body["briefing"]["horizons"]) == 4
    assert body["forecast"]["interval_low"] < body["forecast"]["point_estimate"]
    assert {e["source_node_id"] for e in body["dag"]["edges"]} >= {"avg_spread_pip"}
    assert [s["id"] for s in body["shocks"]] == ["competitor_payout_increase"]
    ids = {o["opportunity_id"] for o in body["briefing"]["opportunities"]}
    assert (
        ids and set(body["stage_requests"]) == ids
    )  # every opportunity can be staged through the hub
    request = next(iter(body["stage_requests"].values()))
    assert request["metadata"]["partner_ids"] == [request["target_entity_id"]]


def test_simulate_returns_the_computed_result_and_refuses_an_untested_shock(
    client: TestClient,
) -> None:
    ok = client.post(
        "/api/cockpit/simulate",
        json={"shock_param": "competitor_payout_increase", "magnitude_pct": 10},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["attribution_sum_pct"] == 100.0 and body["latency_ms"] < 200.0
    assert body["mitigations"] and body["projected_changes"]["projected_revenue_impact_usd"] < 0
    bad = client.post(
        "/api/cockpit/simulate", json={"shock_param": "competitor_spread_cut", "magnitude_pct": 10}
    )
    assert bad.status_code == 422 and "causal" in bad.json()["detail"]
