"""Replaying an answer's figures through the governed port: each one derived again, compared, never assumed."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import copilot_verify, ratelimit
from eios.cockpit.server import app
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.readmodels import ReadModels
from tests.ontology.port.conftest import seeded_geo, who

PATH = "/api/cockpit/copilot/verify"


@pytest.fixture(scope="module")
def models() -> ReadModels:
    built = replace(ReadModels.default(), geo=seeded_geo())
    build_port(built)
    return built


@pytest.fixture
def client(models: ReadModels, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(copilot_verify, "_models", lambda: models)
    yield TestClient(app)


def _shown(models: ReadModels, fact_id: str) -> float:
    return models.facts.resolve(who("geospatial"), fact_id).value


def test_every_figure_derived_again_matches(client: TestClient, models: ReadModels) -> None:
    ids = ["geo.exit:GW-NG-X00:flagged_accounts", "geo.corridor:ID>MM:volume_usd"]
    figures = [{"fact_id": i, "value": _shown(models, i)} for i in ids]
    body = client.post(PATH, json={"role": "geospatial", "figures": figures}).json()
    assert body["checked"] == body["matched"] == 2
    assert all(r["match"] and r["error"] is None for r in body["rows"])


def test_a_figure_that_differs_is_reported_as_a_mismatch(
    client: TestClient, models: ReadModels
) -> None:
    fact = "geo.exit:GW-NG-X00:flagged_accounts"
    body = client.post(
        PATH,
        json={
            "role": "geospatial",
            "figures": [{"fact_id": fact, "value": _shown(models, fact) + 1}],
        },
    ).json()
    assert body["matched"] == 0 and body["rows"][0]["match"] is False


def test_a_figure_that_cannot_be_derived_again_is_never_a_match(client: TestClient) -> None:
    rows = client.post(
        PATH,
        json={
            "role": "geospatial",
            "figures": [{"fact_id": "geo.exit:GW-XX-X99:flagged_accounts", "value": 1}],
        },
    ).json()["rows"]
    assert rows[0]["match"] is False and rows[0]["error"] == "NOT_FOUND"


def test_the_replay_runs_as_the_workstation_asked_for(client: TestClient) -> None:
    rows = client.post(
        PATH,
        json={
            "role": "partner_manager",
            "figures": [{"fact_id": "geo.exit:GW-NG-X00:flagged_accounts", "value": 22}],
        },
    ).json()["rows"]
    assert rows[0]["error"] == "FORBIDDEN_ROLE"


@pytest.mark.parametrize(
    "body",
    [
        {
            "role": "admin",
            "figures": [{"fact_id": "geo.exit:GW-NG-X00:flagged_accounts", "value": 1}],
        },
        {"role": "geospatial", "figures": []},
        {"role": "geospatial", "figures": [{"fact_id": "x:y:z", "value": 1}] * 21},
    ],
)
def test_a_malformed_request_is_refused(client: TestClient, body: dict[str, object]) -> None:
    assert client.post(PATH, json=body).status_code == 422


@pytest.fixture
def limited(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("EIOS_RATE_LIMITS", "on")
    ratelimit.reset()
    yield client
    ratelimit.reset()


ONE = {
    "role": "geospatial",
    "figures": [{"fact_id": "geo.exit:GW-NG-X00:flagged_accounts", "value": 1}],
}


def test_checks_over_the_limit_get_an_honest_429(
    limited: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Each check calls the port again (a graph job for an exit), so it is capped like the questions are.
    monkeypatch.setenv("EIOS_RATE_VERIFY_PER_USER", "2/minute")
    assert [limited.post(PATH, json=ONE).status_code for _ in range(2)] == [200, 200]
    refused = limited.post(PATH, json=ONE)
    assert refused.status_code == 429 and 1 <= int(refused.headers["Retry-After"]) <= 60
    assert "Too many checks" in refused.json()["detail"]


def test_checking_an_answer_does_not_spend_the_question_budget(
    limited: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EIOS_RATE_COPILOT_PER_USER", "1/minute")
    assert [limited.post(PATH, json=ONE).status_code for _ in range(3)] == [200, 200, 200]
    stats = ratelimit.LIMITER.get_window_stats(
        ratelimit._items("1/minute", "1/minute")[0], "copilot", "anonymous"
    )
    assert stats.remaining == 1  # no question counted
