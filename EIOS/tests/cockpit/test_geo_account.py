"""One account's geography as case evidence, and the shared exits on the map payload."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import geo
from eios.cockpit.geo_account import account_payload
from eios.cockpit.geo_view import flows_payload
from eios.cockpit.server import app
from eios.dataplane.aml_geo import GeoSnapshot, run_geo_engine
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.graph.store import GraphUnavailable, LocalGraphStore
from eios.graph.tables import build_tables

TIERS = {"MM": "high", "VG": "medium", "IQ": "medium"}
CENTROIDS = Path(__file__).parents[1] / "fixtures" / "geo" / "country_centroids.json"
POSITIONS = {c: (p[0], p[1]) for c, p in json.loads(CENTROIDS.read_text())["positions"].items()}
TRUTH_WORDS = ("malicious", "mule", "ring_member", "traveller", "planted", "truth")


@pytest.fixture(scope="module")
def snap() -> GeoSnapshot:
    return run_geo_engine(build_aml_world(AmlWorldConfig()), TIERS, POSITIONS)


@pytest.fixture(scope="module")
def store(snap: GeoSnapshot) -> LocalGraphStore:
    return LocalGraphStore(build_tables(snap.world, TIERS))


def _ring_member(snap: GeoSnapshot) -> str:
    flagged = snap.clients[snap.clients["exit_flag"] & snap.clients["jump_flag"]]
    return str(sorted(flagged["client_id"])[0])


def test_an_exit_user_shows_its_exit_its_jumps_and_its_links(
    snap: GeoSnapshot, store: LocalGraphStore
) -> None:
    account = _ring_member(snap)
    p = account_payload(snap, account, store)
    assert p is not None
    json.dumps(p)
    assert p["lenses"]["shared_exit"]["flag"] and p["lenses"]["travel"]["flag"]
    exit_id = p["lenses"]["shared_exit"]["gateway"]
    gw = next(g for g in p["gateways"] if g["gateway_id"] == exit_id)
    assert gw["shared_exit"] and not gw["hub"] and gw["country"] != p["kyc_country"]
    assert p["jumps"]["count"] >= 2
    for jump in p["jumps"]["examples"]:
        assert jump["km"] >= 500 and jump["km"] > 1000 * jump["hours"]
    links = p["neighbourhood"]
    assert links["source"] == "graph.local:aml_geo" and links["error"] is None
    assert any(r["link"] == exit_id for r in links["rows"])
    assert sum(c["sessions"] for c in p["login_countries"]) == p["sessions"]


def test_an_ordinary_account_is_not_flagged_and_its_evidence_says_so(
    snap: GeoSnapshot, store: LocalGraphStore
) -> None:
    quiet = snap.clients[
        ~snap.clients["exit_flag"] & ~snap.clients["jump_flag"] & ~snap.clients["mismatch_flag"]
    ]
    p = account_payload(snap, str(sorted(quiet["client_id"])[0]), store)
    assert p is not None
    assert not any(v["flag"] for v in p["lenses"].values())


def test_unknown_accounts_are_none(snap: GeoSnapshot, store: LocalGraphStore) -> None:
    assert account_payload(snap, "CR00000000", store) is None


class _Down:
    backend = "bigquery"

    def run(self, query: str, params: Any) -> Any:
        raise GraphUnavailable("warehouse unreachable")


def test_a_graph_outage_empties_only_the_links_and_says_why(snap: GeoSnapshot) -> None:
    p = account_payload(snap, _ring_member(snap), _Down())
    assert p is not None
    assert p["neighbourhood"]["rows"] is None and "unreachable" in p["neighbourhood"]["error"]
    assert p["lenses"]["shared_exit"]["flag"]  # the rest of the evidence stands


def test_without_positions_travel_is_not_assessable_never_zero(store: LocalGraphStore) -> None:
    blind = run_geo_engine(build_aml_world(AmlWorldConfig()), TIERS)
    p = account_payload(blind, "CR84920", store)
    assert p is not None and p["jumps"] is None and not p["lenses"]["travel"]["assessable"]


def test_the_map_payload_lists_the_shared_exits_and_counts_the_hubs(snap: GeoSnapshot) -> None:
    payload = flows_payload(snap)
    exits = payload["gateways"]
    assert len(exits) == len(
        snap.world.truth.geo.ring_exits
    )  # one per ring, nothing else on this world
    assert payload["hubs_suppressed"] >= 1
    top = exits[0]
    assert top["accounts"] == sum(h["accounts"] for h in top["home_countries"])
    assert all(h["iso2"] != top["country"] for h in top["home_countries"])
    text = json.dumps(payload).lower()
    assert not any(word in text for word in TRUTH_WORDS)


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_route_serves_an_account_and_404s_unknown_or_malformed_ids(
    client: TestClient, snap: GeoSnapshot, store: LocalGraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geo, "geo_snapshot", lambda: snap)
    monkeypatch.setattr(geo, "graph_store", lambda: store)
    ok = client.get("/api/cockpit/geo/accounts/CR84920")
    assert ok.status_code == 200 and ok.json()["account_id"] == "CR84920"
    assert client.get("/api/cockpit/geo/accounts/CR00000000").status_code == 404
    assert client.get("/api/cockpit/geo/accounts/robert';drop").status_code == 404


def test_route_is_a_plain_503_without_an_engine_plane(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geo, "geo_snapshot", lambda: None)
    response = client.get("/api/cockpit/geo/accounts/CR84920")
    assert response.status_code == 503 and response.json()["detail"] == "geo_unavailable"
