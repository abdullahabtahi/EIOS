"""The list-change route: what an FATF plenary or an EU amendment does to this book, as the map shows it."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import geo
from eios.cockpit.server import app
from eios.dataplane.geo_readmodel import StaticGeo
from tests.ontology.port.conftest import seeded_geo


@pytest.fixture
def client() -> Iterator[TestClient]:
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> StaticGeo:
    plane = seeded_geo()
    monkeypatch.setattr(geo, "geo_snapshot", lambda: plane.snap)
    monkeypatch.setattr(geo, "graph_store", lambda: plane.store)
    return plane


def test_the_fatf_change_is_served_by_default(client: TestClient, served: StaticGeo) -> None:
    body = client.get("/api/cockpit/geo/list-changes").json()
    assert body["list_id"] == "fatf"
    assert {r["iso2"] for r in body["added"]["countries"]} == {"IQ", "BA"}
    assert body["graph"]["source"] == "graph.local:aml_geo"


def test_the_eu_change_names_the_delisted_countries_with_their_exposure(
    client: TestClient, served: StaticGeo
) -> None:
    body = client.get("/api/cockpit/geo/list-changes", params={"list_id": "eu"}).json()
    removed = {r["iso2"]: r for r in body["removed"]["countries"]}
    assert removed["NG"]["registered_accounts"] > 0 and removed["NG"]["linked_accounts"] is not None
    assert body["before"]["label"] != body["after"]["label"]


def test_an_unknown_list_is_refused(client: TestClient, served: StaticGeo) -> None:
    assert client.get("/api/cockpit/geo/list-changes", params={"list_id": "ofac"}).status_code == 422


def test_without_an_engine_plane_it_is_a_plain_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geo, "geo_snapshot", lambda: None)
    response = client.get("/api/cockpit/geo/list-changes")
    assert response.status_code == 503 and response.json()["detail"] == "geo_unavailable"
