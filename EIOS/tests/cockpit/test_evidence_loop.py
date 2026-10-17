"""The N3 loop, end to end: a geo turn proposes a hold, its evidence is sealed, staging signs the bundle's id with the
intent, two other people approve it, and replaying the bundle gives back every figure it holds."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eios.assistant.config import AssistantSettings
from eios.assistant.runtime import AssistantRuntime
from eios.assistant.scripted_model import ScriptedLlm, call, draft
from eios.assistant.sessions import build_session_service
from eios.cockpit import assistant_gateway, evidence_routes, server
from eios.evidence.bundle import ref
from eios.evidence.store import evidence_store
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.service import GovernedToolPort
from tests.ontology.port.conftest import seeded_geo

QUERY = "/api/cockpit/copilot/query"
STAGE = "/api/cockpit/actions/stage"
AUTHORIZE = "/api/cockpit/actions/authorize"
HOLD = "Put a hold on the withdrawal for CR84920."


@pytest.fixture(scope="module")
def port() -> GovernedToolPort:
    return build_port(replace(ReadModels.default(), geo=seeded_geo()))


@pytest.fixture
def client(port: GovernedToolPort, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    settings = AssistantSettings.from_env(
        {"EIOS_ENVIRONMENT": "test", "EIOS_ASSISTANT_PREFETCH": "0"}
    )
    runtime = AssistantRuntime(
        port=port,
        settings=settings,
        session_service=build_session_service(settings),
        model=ScriptedLlm(
            steps=[
                call("propose_hold", entity_id="CR84920"),
                draft("A hold is proposed for review."),
            ]
        ),
    )
    assistant_gateway.set_runtime_for_testing(runtime)
    monkeypatch.setattr(
        evidence_routes, "_port", lambda: port
    )  # replay reads the same plane the turn read
    yield TestClient(server.app)
    assistant_gateway.set_runtime_for_testing(None)


def _ask(client: TestClient, question: str = HOLD) -> dict[str, Any]:
    response = client.post(QUERY, json={"query": question, "role": "geospatial"})
    assert response.status_code == 200, response.text
    return response.json()


def test_a_hold_proposed_from_the_map_is_sealed_signed_approved_and_replays_equal(
    client: TestClient,
) -> None:
    body = _ask(client)
    bundle_id = body["evidence_bundle_id"]
    assert bundle_id and len(bundle_id) == 64
    stage_request = body["proposals"][0]["stage_request"]
    assert stage_request["evidence_bundle_id"] == bundle_id  # the browser forwards it unchanged

    staged = client.post(STAGE, json={**stage_request, "initiator_officer_id": "OFFICER_A"})
    assert staged.status_code == 200, staged.text
    intent_id = staged.json()["card"]["intent_id"]
    token = server.governance.hub.find(intent_id)
    assert token is not None and ref(bundle_id) in token.evidence_refs
    assert server.governance.hub.signer.verify_token(
        token
    )  # the signature covers the evidence reference

    assert (
        client.post(
            AUTHORIZE, json={"intent_id": intent_id, "authorizer_id": "OFFICER_A"}
        ).status_code
        == 400
    )
    first = client.post(AUTHORIZE, json={"intent_id": intent_id, "authorizer_id": "OFFICER_B"})
    second = client.post(AUTHORIZE, json={"intent_id": intent_id, "authorizer_id": "OFFICER_C"})
    assert (first.json()["status"], second.json()["status"]) == ("PENDING_SECOND_EYE", "COMMITTED")

    shown = client.get(f"/api/cockpit/evidence/{bundle_id}").json()
    assert shown["intact"] and shown["question"] == HOLD
    assert [c["name"] for c in shown["calls"]] == ["propose_hold"]
    manifest = shown["manifest"]  # what produced the answer is sealed with what it read
    assert manifest["workstation"] == "geospatial" and shown["schema"].endswith("/v2")
    assert len(manifest["instruction_sha256"]) == 64 and len(manifest["toolset"]["sha256"]) == 64

    replayed = client.post(f"/api/cockpit/evidence/{bundle_id}/replay").json()
    assert replayed["intact"] and replayed["equal"]
    assert replayed["figures"] > 0 and replayed["differing"] == 0
    assert replayed["manifest"] == {"status": "unchanged", "changed": []}


def test_a_replay_names_every_figure_that_changed_since_sealing(
    client: TestClient, port: GovernedToolPort, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_id = _ask(client)["evidence_bundle_id"]

    class _Moved:
        def call(self, principal: Any, tool: str, arguments: dict[str, Any]) -> Any:
            outcome = port.call(principal, tool, arguments)
            moved = outcome.result.model_copy(update={"expected_effect_low": 1.0})
            return type(outcome)(tool=outcome.tool, result=moved)

    monkeypatch.setattr(evidence_routes, "_port", lambda: _Moved())
    replayed = client.post(f"/api/cockpit/evidence/{bundle_id}/replay").json()
    assert not replayed["equal"] and replayed["differing"] == 1
    assert replayed["calls"][0]["differences"][0]["fact_id"].endswith(":expected_effect_low")


def test_a_replay_says_when_the_setup_that_answered_has_changed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_id = _ask(client)["evidence_bundle_id"]
    runtime = assistant_gateway.get_runtime()
    monkeypatch.setattr(runtime, "_settings", replace(runtime._settings, plain_figures=False))
    runtime._manifests.clear()
    replayed = client.post(f"/api/cockpit/evidence/{bundle_id}/replay").json()
    assert replayed["equal"]  # the data came back the same
    assert replayed["manifest"]["status"] == "changed"
    assert "instruction_sha256" in replayed["manifest"]["changed"]


def test_staging_with_evidence_that_is_unknown_altered_or_about_someone_else_is_refused(
    client: TestClient,
) -> None:
    body = _ask(client)
    bundle_id, stage_request = body["evidence_bundle_id"], body["proposals"][0]["stage_request"]
    unknown = client.post(STAGE, json={**stage_request, "evidence_bundle_id": "0" * 64})
    assert unknown.status_code == 422
    other = client.post(STAGE, json={**stage_request, "target_entity_id": "CR11111"})
    assert other.status_code == 422 and "not about this entity" in other.json()["detail"]

    records = evidence_store()._records
    records.put(bundle_id, {**records.get(bundle_id), "question": "edited after sealing"})
    assert client.post(STAGE, json=stage_request).status_code == 409
    assert client.get(f"/api/cockpit/evidence/{bundle_id}").status_code == 409


def test_a_turn_that_decides_nothing_is_not_sealed(port: GovernedToolPort) -> None:
    settings = AssistantSettings.from_env(
        {"EIOS_ENVIRONMENT": "test", "EIOS_ASSISTANT_PREFETCH": "0"}
    )
    runtime = AssistantRuntime(
        port=port,
        settings=settings,
        session_service=build_session_service(settings),
        model=ScriptedLlm(steps=[draft("Start with the shared exits.")]),
    )
    assistant_gateway.set_runtime_for_testing(runtime)
    try:
        body = (
            TestClient(server.app)
            .post(QUERY, json={"query": "Where to?", "role": "geospatial"})
            .json()
        )
    finally:
        assistant_gateway.set_runtime_for_testing(None)
    assert body["evidence_bundle_id"] is None
