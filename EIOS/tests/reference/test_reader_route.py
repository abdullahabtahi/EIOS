"""The reference reader shapes warehouse rows into one payload; the route serves it or says it is unavailable."""

import json

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import geo
from eios.cockpit.server import app
from eios.reference.reader import ReferenceReader, ReferenceUnavailable, reader_from_env

ROWS = [
    {
        "iso2": "PA",
        "name": "Panama",
        "boundary": json.dumps({"type": "Polygon", "coordinates": []}),
        "lng": -80.1,
        "lat": 8.5,
        "fatf_list": None,
        "entities_incorporated": 48692,
        "entities_linked": 18345,
        "boundary_as_of": "2026-09-23",
        "fatf_as_of": None,
        "precedent_as_of": "2026-09-09",
        "indicators": [
            {"code": "NY.GDP.PCAP.CD", "name": "GDP per capita", "year": 2020, "value": 12510.0}
        ],
    },
    {
        "iso2": "IR",
        "name": "Iran",
        "boundary": json.dumps({"type": "Polygon", "coordinates": []}),
        "lng": 53.7,
        "lat": 32.4,
        "fatf_list": "call_for_action",
        "entities_incorporated": None,
        "entities_linked": None,
        "boundary_as_of": "2026-09-23",
        "fatf_as_of": "2026-06-19",
        "precedent_as_of": None,
        "indicators": [],
    },
]


class _Client:
    def __init__(self, rows: list[dict]) -> None:
        self.rows, self.calls = rows, 0

    def query(self, sql, job_config=None, location=None):
        self.calls += 1
        return self

    def result(self) -> list[dict]:
        return self.rows


def test_payload_has_countries_with_parsed_geometry_and_sources() -> None:
    payload = ReferenceReader("test-project", client=_Client(ROWS)).world()
    by = {c["iso2"]: c for c in payload["countries"]}
    assert by["PA"]["boundary"]["type"] == "Polygon"
    assert by["PA"]["entities_incorporated"] == 48692
    assert by["IR"]["fatf_list"] == "call_for_action"
    assert payload["sources"]["fatf"]["as_of"] == "2026-06-19"
    assert payload["sources"]["offshore_precedent"]["as_of"] == "2026-09-09"


def test_a_country_with_no_measurement_reports_none_not_zero() -> None:
    by = {
        c["iso2"]: c
        for c in ReferenceReader("test-project", client=_Client(ROWS)).world()["countries"]
    }
    assert by["IR"]["entities_incorporated"] is None and by["PA"]["fatf_list"] is None


def test_the_snapshot_is_read_once_and_cached() -> None:
    client = _Client(ROWS)
    reader = ReferenceReader("test-project", client=client)
    reader.world()
    reader.world()
    assert client.calls == 1


def test_an_empty_warehouse_is_unavailable_not_an_empty_map() -> None:
    with pytest.raises(ReferenceUnavailable):
        ReferenceReader("test-project", client=_Client([])).world()


def test_reader_from_env_is_none_unless_the_warehouse_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EIOS_WARM_BACKEND", raising=False)
    monkeypatch.delenv("EIOS_WARM_PROJECT", raising=False)
    assert reader_from_env() is None
    monkeypatch.setenv("EIOS_WARM_BACKEND", "local")
    assert reader_from_env() is None


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_route_serves_the_snapshot(client: TestClient) -> None:
    app.dependency_overrides[geo.get_reader] = lambda: ReferenceReader(
        "test-project", client=_Client(ROWS)
    )
    response = client.get("/api/cockpit/geo/reference")
    assert response.status_code == 200
    assert len(response.json()["countries"]) == 2


def test_route_says_unavailable_with_503_when_not_configured(client: TestClient) -> None:
    app.dependency_overrides[geo.get_reader] = lambda: None
    response = client.get("/api/cockpit/geo/reference")
    assert response.status_code == 503
    assert response.json()["detail"] == "reference_unavailable"


@pytest.mark.requires_cloud
def test_live_reference_layer_reads_from_the_warehouse() -> None:
    """Needs EIOS_TEST_CLOUD=1 and EIOS_WARM_PROJECT; the fake client cannot catch a query BigQuery rejects."""
    import os

    reader = ReferenceReader(os.environ["EIOS_WARM_PROJECT"])
    payload = reader.world()
    by = {c["iso2"]: c for c in payload["countries"]}
    assert len(by) > 200
    assert by["IR"]["fatf_list"] == "call_for_action"
    assert (by["BS"]["entities_incorporated"] or 0) > 100_000
    assert any(i["code"] == "NY.GDP.PCAP.CD" for i in by["BS"]["indicators"])


def test_a_malformed_project_id_is_refused_before_it_reaches_sql() -> None:
    with pytest.raises(ValueError, match="project id"):
        ReferenceReader("x`; DROP TABLE y; --")
