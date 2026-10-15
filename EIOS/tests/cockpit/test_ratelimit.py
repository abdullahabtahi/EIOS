"""The copilot, the only path that spends model budget, is capped per operator and per instance; a refusal is an honest 429."""

import pytest
from fastapi.testclient import TestClient

from eios.assistant.scripted_model import call, draft
from eios.cockpit import assistant_gateway, ratelimit, server
from eios.cockpit.auth import Operator, current_operator
from tests.assistant.conftest import make_runtime

PATH = "/api/cockpit/copilot/query"
BODY = {
    "query": "What is the discrepancy?",
    "role": "aml_investigator",
    "activeEntityId": "CR84920",
}
FIGURE = "{{fact:aml.dossier:CR84920:discrepancy_multiplier}}"


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EIOS_RATE_LIMITS", "on")
    ratelimit.reset()
    state = {"uid": "uid-1"}
    server.app.dependency_overrides[current_operator] = lambda: Operator(
        uid=state["uid"], email=None, role="analyst"
    )
    runtime, _ = make_runtime(
        [call("get_aml_dossier", entity_id="CR84920"), draft(f"It is {FIGURE}.")] * 8
    )
    assistant_gateway.set_runtime_for_testing(runtime)
    yield TestClient(server.app), state
    server.app.dependency_overrides.pop(current_operator, None)
    assistant_gateway.set_runtime_for_testing(None)
    ratelimit.reset()


def test_the_question_over_the_per_minute_limit_gets_a_429_with_retry_after(
    api, monkeypatch
) -> None:
    client, _ = api
    monkeypatch.setenv("EIOS_RATE_COPILOT_PER_USER", "2/minute")
    assert [client.post(PATH, json=BODY).status_code for _ in range(2)] == [200, 200]
    refused = client.post(PATH, json=BODY)
    assert refused.status_code == 429
    assert 1 <= int(refused.headers["Retry-After"]) <= 60
    assert "Try again in" in refused.json()["detail"]


def test_a_refused_question_is_not_counted_so_waiting_it_out_is_enough(api, monkeypatch) -> None:
    client, _ = api
    monkeypatch.setenv("EIOS_RATE_COPILOT_PER_USER", "1/minute")
    assert client.post(PATH, json=BODY).status_code == 200
    waits = {int(client.post(PATH, json=BODY).headers["Retry-After"]) for _ in range(3)}
    assert max(waits) - min(waits) <= 1  # hammering did not push the wait further out


def test_another_operator_is_not_held_by_someones_limit(api, monkeypatch) -> None:
    client, state = api
    monkeypatch.setenv("EIOS_RATE_COPILOT_PER_USER", "1/minute")
    assert client.post(PATH, json=BODY).status_code == 200
    assert client.post(PATH, json=BODY).status_code == 429
    state["uid"] = "uid-2"
    assert client.post(PATH, json=BODY).status_code == 200


def test_the_instance_wide_daily_cap_stops_everyone(api, monkeypatch) -> None:
    client, state = api
    monkeypatch.setenv("EIOS_RATE_COPILOT_GLOBAL", "2/day")
    assert client.post(PATH, json=BODY).status_code == 200
    state["uid"] = "uid-2"
    assert client.post(PATH, json=BODY).status_code == 200
    state["uid"] = "uid-3"
    assert client.post(PATH, json=BODY).status_code == 429


def test_a_question_longer_than_the_cap_is_refused_before_it_reaches_the_model(api) -> None:
    client, _ = api
    assert client.post(PATH, json={**BODY, "query": "x" * 2001}).status_code == 422
    assert client.post(PATH, json={**BODY, "query": ""}).status_code == 422


def test_with_limits_off_nothing_is_refused(api, monkeypatch) -> None:
    client, _ = api
    monkeypatch.setenv("EIOS_RATE_LIMITS", "off")
    monkeypatch.setenv("EIOS_RATE_COPILOT_PER_USER", "1/minute")
    assert all(client.post(PATH, json=BODY).status_code == 200 for _ in range(4))


def test_a_mistyped_limit_setting_falls_back_to_the_default_instead_of_failing_every_question(
    api, monkeypatch, caplog
) -> None:
    client, _ = api
    monkeypatch.setenv("EIOS_RATE_COPILOT_PER_USER", "twenty a minute")
    with caplog.at_level("ERROR", logger="eios.ratelimit"):
        assert (
            client.post(PATH, json=BODY).status_code == 200
        )  # still served, under the default limit
    assert "invalid rate limit" in caplog.text
