"""The geo flows payload: the engine's results shaped for the map, with no truth in it and no invented tiers."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import geo
from eios.cockpit.geo_view import flows_payload
from eios.cockpit.server import app
from eios.dataplane.aml_geo import GeoSnapshot, run_geo_engine
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world

TIERS = {"MM": "high", "VG": "medium", "VN": "medium"}


@pytest.fixture(scope="module")
def snap() -> GeoSnapshot:
    return run_geo_engine(build_aml_world(AmlWorldConfig()), TIERS)


def test_payload_is_json_serialisable_and_states_its_origin(snap: GeoSnapshot) -> None:
    payload = flows_payload(snap)
    json.dumps(payload)
    assert payload["source"] and payload["as_of"].startswith("2026-10-14")
    assert payload["tiers_known"] is True


def test_corridors_are_cross_border_with_tiers_and_sorted_by_volume(snap: GeoSnapshot) -> None:
    rows = flows_payload(snap)["corridors"]
    assert rows and all(r["origin"] != r["destination"] for r in rows)
    assert {r["tier"] for r in rows} <= {"low", "medium", "high"}
    volumes = [r["volume_usd"] for r in rows]
    assert volumes == sorted(volumes, reverse=True)
    assert any(r["tier"] == "high" and "MM" in (r["origin"], r["destination"]) for r in rows)


def test_mismatch_pairs_aggregate_flagged_clients_with_a_few_sample_accounts(
    snap: GeoSnapshot,
) -> None:
    pairs = flows_payload(snap)["mismatch_pairs"]
    assert sum(p["accounts"] for p in pairs) == int(snap.clients["mismatch_flag"].sum())
    assert all(p["kyc_country"] != p["ip_country"] for p in pairs)
    assert all(1 <= len(p["sample_accounts"]) <= 5 for p in pairs)


def test_the_payload_carries_no_planted_truth(snap: GeoSnapshot) -> None:
    payload = flows_payload(snap)
    assert "quality" not in payload  # the evaluation is for logs and the CLI, not the cockpit
    text = json.dumps(payload).lower()
    for forbidden in ("truth", "planted", "malicious", "benign", "risky_clients"):
        assert forbidden not in text


def test_coverage_states_how_many_clients_each_lens_can_judge(snap: GeoSnapshot) -> None:
    cov = flows_payload(snap)["coverage"]
    assert cov["clients"] == len(snap.clients)
    assert (
        0 < cov["mismatch_assessable"] < cov["clients"]
    )  # some clients have too few events to judge
    assert cov["mismatch_assessable"] == int(snap.clients["mismatch_assessable"].sum())
    assert 0 < cov["corridor_assessable"] <= cov["clients"]
    unrated = flows_payload(run_geo_engine(snap.world, {}))
    assert (
        unrated["coverage"]["corridor_assessable"] is None
    )  # no tiers: the corridor lens judged nobody


def test_unknown_tiers_are_null_never_low(snap: GeoSnapshot) -> None:
    blind = run_geo_engine(snap.world, {})
    payload = flows_payload(blind)
    assert payload["tiers_known"] is False
    assert all(r["tier"] is None for r in payload["corridors"])
    assert payload["exposure"] is None


def test_exposure_sums_to_the_corridor_volume(snap: GeoSnapshot) -> None:
    payload = flows_payload(snap)
    exposure = payload["exposure"]
    assert sum(exposure.values()) == pytest.approx(
        sum(r["volume_usd"] for r in payload["corridors"]), rel=1e-6
    )


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_route_serves_the_payload(
    client: TestClient, snap: GeoSnapshot, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geo, "geo_snapshot", lambda: snap)
    response = client.get("/api/cockpit/geo/flows")
    assert response.status_code == 200
    assert response.json()["corridors"]


def test_route_is_a_plain_503_when_there_is_no_engine_plane(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geo, "geo_snapshot", lambda: None)
    response = client.get("/api/cockpit/geo/flows")
    assert response.status_code == 503
    assert response.json()["detail"] == "geo_unavailable"
