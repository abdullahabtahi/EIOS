"""The prepared-brief routes: read a brief, 404 when none was prepared, and a refresh that builds the top ones in the
background under approver roles only."""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from eios.ambient.brief import evidence_only
from eios.assistant.config import AssistantSettings
from eios.assistant.runtime import AssistantRuntime
from eios.assistant.scripted_model import ScriptedLlm, call, draft
from eios.assistant.sessions import build_session_service
from eios.cockpit import ambient_routes, server
from eios.cockpit.auth import Operator, current_operator
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.readmodels import ReadModels

BRIEF = "/api/cockpit/ambient/briefs/CR84920"
REFRESH = "/api/cockpit/ambient/refresh"
FIGURE = "{{fact:aml.dossier:CR84920:discrepancy_multiplier}}"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    settings = AssistantSettings.from_env(
        {"EIOS_ENVIRONMENT": "test", "EIOS_ASSISTANT_PREFETCH": "0"}
    )
    runtime = AssistantRuntime(
        port=evidence_only(build_port(ReadModels.default())),
        settings=settings,
        session_service=build_session_service(settings),
        model=ScriptedLlm(
            steps=[
                call("get_aml_dossier", entity_id="CR84920"),
                draft(f"The discrepancy is {FIGURE}."),
            ]
        ),
    )
    ambient_routes.reset_for_testing()
    monkeypatch.setattr(ambient_routes, "_runtime", lambda: runtime)
    monkeypatch.setattr(ambient_routes, "top_entities", lambda n: ["CR84920"][:n])
    with TestClient(server.app) as test_client:  # keeps the loop alive for the background refresh
        yield test_client
    ambient_routes.reset_for_testing()
    server.app.dependency_overrides.pop(current_operator, None)


def _wait_for_brief(client: TestClient) -> dict:
    for _ in range(100):
        response = client.get(BRIEF)
        if response.status_code == 200:
            return response.json()
        time.sleep(0.05)
    pytest.fail("the brief was not prepared in time")


def test_no_brief_is_a_404_that_says_none_was_prepared(client: TestClient) -> None:
    response = client.get(BRIEF)
    assert response.status_code == 404
    assert "no brief has been prepared" in response.json()["detail"]


def test_an_invalid_entity_id_is_refused(client: TestClient) -> None:
    assert client.get("/api/cockpit/ambient/briefs/..%2Fsecret").status_code in {404, 422}
    assert client.get("/api/cockpit/ambient/briefs/a b").status_code == 422


def test_a_refresh_builds_the_brief_and_the_route_then_serves_it(client: TestClient) -> None:
    started = client.post(REFRESH)
    assert started.status_code == 202 and started.json()["started"] is True
    body = _wait_for_brief(client)
    assert body["stale"] is False
    assert "16x" in body["response"] and body["provenance_citations"]
    assert body["entity_id"] == "CR84920" and body["prepared_at"] < body["expires_at"]
    assert "proposals" not in body and body["steps"] == ["get_aml_dossier"]


def test_only_approver_roles_may_refresh(client: TestClient) -> None:
    server.app.dependency_overrides[current_operator] = lambda: Operator(
        uid="u1", email=None, role="analyst"
    )
    assert client.post(REFRESH).status_code == 403
    server.app.dependency_overrides[current_operator] = lambda: Operator(
        uid="u2", email=None, role="approver"
    )
    assert client.post(REFRESH).status_code == 202


def test_a_second_refresh_while_one_runs_does_not_start_another(client: TestClient) -> None:
    assert client.post(REFRESH).json()["started"] is True
    again = client.post(REFRESH)
    assert again.status_code == 202  # accepted, but at most one runs at a time
    _wait_for_brief(client)
