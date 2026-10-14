"""The copilot endpoint takes identity and scope from the server, not from what the caller says (spec 023 T025)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import server
from eios.cockpit.auth import Operator, current_operator
from eios.conversation.models import ConversationQueryResponse
from eios.conversation.models import OperatorRole as EngineRole

PATH = "/api/cockpit/copilot/query"


@pytest.fixture(autouse=True)
def _legacy_copilot(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests cover the legacy copilot, which the ADK assistant now replaces as the default."""
    monkeypatch.setenv("EIOS_ASSISTANT_RUNTIME", "legacy")


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake(**kwargs: Any) -> ConversationQueryResponse:
        calls.append(kwargs)
        return ConversationQueryResponse(session_id="s", response_markdown="ok")

    monkeypatch.setattr(server.copilot_engine, "process_query", fake)
    return calls


@pytest.fixture
def client() -> TestClient:
    return TestClient(server.app)


@pytest.fixture
def as_operator() -> Iterator[None]:
    server.app.dependency_overrides[current_operator] = lambda: Operator(
        uid="uid-42", email=None, role="analyst"
    )
    yield
    server.app.dependency_overrides.pop(current_operator, None)


@pytest.mark.parametrize("workstation", [r.value for r in EngineRole])
def test_the_requested_workstation_is_the_scope(
    client: TestClient, seen: list[dict[str, Any]], workstation: str
) -> None:
    assert client.post(PATH, json={"query": "hi", "role": workstation}).status_code == 200
    assert seen[-1]["role"] is EngineRole(workstation)


def test_the_role_is_case_insensitive_but_never_widened_to_a_default(
    client: TestClient, seen: list[dict[str, Any]]
) -> None:
    client.post(PATH, json={"query": "hi", "role": "PARTNER_MANAGER"})
    assert seen[-1]["role"] is EngineRole.PARTNER_MANAGER


@pytest.mark.parametrize("claimed", ["admin", "compliance_head", "", "executive; drop"])
def test_an_unknown_role_is_refused_not_defaulted_to_executive(
    client: TestClient, seen: list[dict[str, Any]], claimed: str
) -> None:
    response = client.post(PATH, json={"query": "hi", "role": claimed})
    assert response.status_code == 422
    assert seen == []


def test_the_session_belongs_to_the_verified_operator(
    client: TestClient, seen: list[dict[str, Any]], as_operator: None
) -> None:
    client.post(PATH, json={"query": "hi", "role": "executive"})
    assert "uid-42" in seen[-1]["session_id"] and seen[-1]["session_id"] != "sess_default"


def test_two_operators_never_share_a_session(
    client: TestClient, seen: list[dict[str, Any]]
) -> None:
    for uid in ("uid-1", "uid-2"):
        server.app.dependency_overrides[current_operator] = lambda uid=uid: Operator(
            uid=uid, email=None, role="analyst"
        )
        client.post(PATH, json={"query": "hi", "role": "executive"})
    server.app.dependency_overrides.pop(current_operator, None)
    assert seen[0]["session_id"] != seen[1]["session_id"]


def test_both_entity_field_names_are_accepted(
    client: TestClient, seen: list[dict[str, Any]]
) -> None:
    for body in ({"context_entity_id": "PTR-882"}, {"activeEntityId": "PTR-882"}):
        assert (
            client.post(PATH, json={"query": "hi", "role": "partner_manager", **body}).status_code
            == 200
        )
