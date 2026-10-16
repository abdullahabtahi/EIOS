"""The copilot endpoint carries the map's context in and the accepted map moves out (docs/geo-agent.md)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eios.assistant.answer import Answer
from eios.assistant.runtime import TurnOutcome
from eios.cockpit import assistant_gateway, server

PATH = "/api/cockpit/copilot/query"
MOVE = {"kind": "gateway", "id": "GW-NG-X00"}


class _Spy:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run_turn(self, **kwargs: Any) -> TurnOutcome:
        self.calls.append(kwargs)
        return TurnOutcome(answer=Answer(text="ok", view_commands=(MOVE,)))


@pytest.fixture
def seen() -> Iterator[_Spy]:
    spy = _Spy()
    assistant_gateway.set_runtime_for_testing(spy)  # type: ignore[arg-type]
    yield spy
    assistant_gateway.set_runtime_for_testing(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(server.app)


def test_the_map_context_reaches_the_turn_and_the_moves_come_back(
    client: TestClient, seen: _Spy
) -> None:
    context = {"view": "logins", "selection": {"kind": "gateway", "id": "GW-NG-X00"}}
    response = client.post(
        PATH, json={"query": "why?", "role": "geospatial", "mapContext": context}
    )
    assert response.status_code == 200
    assert seen.calls[-1]["entity_context"] == {**context, "basis": None}
    assert response.json()["view_commands"] == [MOVE]


@pytest.mark.parametrize(
    "context",
    [
        {"view": "satellite"},
        {"view": "logins", "selection": {"kind": "planet", "id": "X"}},
        {"view": "logins", "selection": {"kind": "gateway", "id": "GW;DROP TABLE"}},
        {"view": "logins", "zoom": 7},
    ],
)
def test_a_map_context_outside_the_vocabulary_is_refused(
    client: TestClient, seen: _Spy, context: dict[str, Any]
) -> None:
    response = client.post(
        PATH, json={"query": "why?", "role": "geospatial", "mapContext": context}
    )
    assert response.status_code == 422 and seen.calls == []


def test_without_a_map_context_the_turn_has_none(client: TestClient, seen: _Spy) -> None:
    assert client.post(PATH, json={"query": "hi", "role": "aml_investigator"}).status_code == 200
    assert seen.calls[-1]["entity_context"] is None
