"""The address check route: a POST (so the address never sits in a URL or an access log), a plain 503 without data."""

import logging

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import geo
from eios.cockpit.server import app
from eios.netintel.lookup import NetSnapshot, SourceStamp
from eios.netintel.sources import ListEntry
from eios.netintel.store import NetUnavailable

PATH = "/api/cockpit/geo/address"
SECRET = "1.0.0.7"


def _snapshot() -> NetSnapshot:
    return NetSnapshot.from_rows(
        v4=[(16777216, 16777471, "AU", 13335)],
        v6=[],
        asns={13335: ("Cloudflare, Inc.", "cloudflare.com")},
        countries={"AU": "Australia"},
        entries=[
            ListEntry("tor_exit", "1.0.0.7/32", ""),
            ListEntry("cloud", "1.0.0.0/24", "Example Cloud, r1"),
        ],
        stamps=(SourceStamp("IPinfo Lite", "2026-10-15"),),
    )


class _Reader:
    def __init__(self, snapshot: NetSnapshot | None = None, error: Exception | None = None) -> None:
        self._snapshot, self._error = snapshot, error

    def snapshot(self) -> NetSnapshot:
        if self._error:
            raise self._error
        assert self._snapshot is not None
        return self._snapshot


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_a_listed_address_comes_back_with_country_network_lists_and_sources(
    client: TestClient,
) -> None:
    app.dependency_overrides[geo.get_net_reader] = lambda: _Reader(_snapshot())
    response = client.post(PATH, json={"address": f" {SECRET} "})
    assert response.status_code == 200
    body = response.json()
    assert body["address"] == SECRET and body["version"] == 4 and body["scope"] == "public"
    assert body["country"] == {"iso2": "AU", "name": "Australia"}
    assert body["network"] == {"asn": 13335, "name": "Cloudflare, Inc.", "domain": "cloudflare.com"}
    assert body["verdict"] == "tor_exit"
    assert body["lists"] == [
        {"list": "tor_exit", "detail": ""},
        {"list": "cloud", "detail": "Example Cloud, r1"},
    ]
    assert body["sources"] == [{"name": "IPinfo Lite", "as_of": "2026-10-15"}]
    assert body["uncovered"] == ["vpn", "datacenter"]


def test_an_address_the_database_does_not_know_has_null_country_not_a_guess(
    client: TestClient,
) -> None:
    app.dependency_overrides[geo.get_net_reader] = lambda: _Reader(_snapshot())
    body = client.post(PATH, json={"address": "8.8.8.8"}).json()
    assert body["country"] is None and body["network"] is None and body["verdict"] == "none_listed"


def test_a_private_address_is_answered_without_a_lookup(client: TestClient) -> None:
    app.dependency_overrides[geo.get_net_reader] = lambda: _Reader(_snapshot())
    body = client.post(PATH, json={"address": "10.1.2.3"}).json()
    assert body["scope"] == "private" and body["verdict"] == "not_public" and body["lists"] == []


@pytest.mark.parametrize("bad", ["", "hello", "1.2.3", "1.2.3.4/24", "999.1.1.1"])
def test_something_that_is_not_an_address_is_a_422(client: TestClient, bad: str) -> None:
    app.dependency_overrides[geo.get_net_reader] = lambda: _Reader(_snapshot())
    response = client.post(PATH, json={"address": bad})
    assert response.status_code == 422


def test_no_snapshot_configured_is_a_plain_503(client: TestClient) -> None:
    app.dependency_overrides[geo.get_net_reader] = lambda: None
    response = client.post(PATH, json={"address": SECRET})
    assert response.status_code == 503 and response.json()["detail"] == "address_check_unavailable"


def test_an_unreadable_snapshot_is_the_same_503_never_a_partial_answer(client: TestClient) -> None:
    app.dependency_overrides[geo.get_net_reader] = lambda: _Reader(
        error=NetUnavailable("no tables")
    )
    assert client.post(PATH, json={"address": SECRET}).status_code == 503
    app.dependency_overrides[geo.get_net_reader] = lambda: _Reader(error=RuntimeError("boom"))
    assert client.post(PATH, json={"address": SECRET}).status_code == 503


def test_the_address_is_never_written_to_the_logs(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    app.dependency_overrides[geo.get_net_reader] = lambda: _Reader(_snapshot())
    with caplog.at_level(logging.DEBUG):
        client.post(PATH, json={"address": SECRET})
        app.dependency_overrides[geo.get_net_reader] = lambda: _Reader(error=RuntimeError("boom"))
        client.post(PATH, json={"address": SECRET})
    assert SECRET not in caplog.text
