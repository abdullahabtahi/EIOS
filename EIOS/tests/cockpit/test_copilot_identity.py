"""The copilot endpoint takes identity and scope from the server, not from what the caller says (spec 023 T025)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eios.assistant.answer import Answer
from eios.assistant.runtime import TurnOutcome
from eios.cockpit import assistant_gateway, server
from eios.cockpit.auth import Operator, current_operator
from eios.ontology.omcp.port.principal import Workstation

PATH = "/api/cockpit/copilot/query"


class _Spy:
    """Stands in for the assistant runtime and records who the turn ran as."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run_turn(self, **kwargs: Any) -> TurnOutcome:
        self.calls.append(kwargs)
        return TurnOutcome(answer=Answer(text="ok"))


@pytest.fixture
def seen() -> Iterator[_Spy]:
    spy = _Spy()
    assistant_gateway.set_runtime_for_testing(spy)  # type: ignore[arg-type]
    yield spy
    assistant_gateway.set_runtime_for_testing(None)


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


@pytest.mark.parametrize("workstation", [w.value for w in Workstation])
def test_the_requested_workstation_is_the_scope(
    client: TestClient, seen: _Spy, workstation: str
) -> None:
    assert client.post(PATH, json={"query": "hi", "role": workstation}).status_code == 200
    assert seen.calls[-1]["principal"].workstation is Workstation(workstation)


def test_the_role_is_case_insensitive_but_never_widened_to_a_default(
    client: TestClient, seen: _Spy
) -> None:
    client.post(PATH, json={"query": "hi", "role": "PARTNER_MANAGER"})
    assert seen.calls[-1]["principal"].workstation is Workstation.PARTNER_MANAGER


@pytest.mark.parametrize("claimed", ["admin", "compliance_head", "", "executive; drop"])
def test_an_unknown_role_is_refused_not_defaulted_to_executive(
    client: TestClient, seen: _Spy, claimed: str
) -> None:
    response = client.post(PATH, json={"query": "hi", "role": claimed})
    assert response.status_code == 422
    assert seen.calls == []


def test_the_turn_runs_as_the_verified_operator(
    client: TestClient, seen: _Spy, as_operator: None
) -> None:
    client.post(PATH, json={"query": "hi", "role": "executive", "uid": "someone-else"})
    assert seen.calls[-1]["principal"].uid == "uid-42"


def test_two_operators_never_share_an_identity(client: TestClient, seen: _Spy) -> None:
    for uid in ("uid-1", "uid-2"):
        server.app.dependency_overrides[current_operator] = lambda uid=uid: Operator(
            uid=uid, email=None, role="analyst"
        )
        client.post(PATH, json={"query": "hi", "role": "executive"})
    server.app.dependency_overrides.pop(current_operator, None)
    assert seen.calls[0]["principal"].uid != seen.calls[1]["principal"].uid


def test_both_entity_field_names_are_accepted(client: TestClient, seen: _Spy) -> None:
    for body in ({"context_entity_id": "PTR-882"}, {"activeEntityId": "PTR-882"}):
        response = client.post(PATH, json={"query": "hi", "role": "partner_manager", **body})
        assert response.status_code == 200
        assert seen.calls[-1]["entity_id"] == "PTR-882"
