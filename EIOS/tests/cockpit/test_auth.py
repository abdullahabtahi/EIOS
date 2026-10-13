"""Operator authentication: Firebase ID tokens in deployed environments, role-based access, identity-bound four-eyes."""

import pytest
from fastapi.testclient import TestClient

from eios.cockpit import server
from eios.cockpit.auth import (
    FirebaseAuthenticator,
    Operator,
    cors_origins,
    default_authenticator,
    get_authenticator,
)

TOKENS = {
    "tok-analyst": {"sub": "u-analyst", "email": "analyst@example.org", "role": "analyst"},
    "tok-approver-1": {"sub": "u-approver-1", "email": "a1@example.org", "role": "approver"},
    "tok-approver-2": {"sub": "u-approver-2", "email": "a2@example.org", "role": "approver"},
    "tok-norole": {"sub": "u-norole", "email": "n@example.org"},
    "tok-badrole": {"sub": "u-bad", "email": "b@example.org", "role": "superuser"},
}


def _fake_verifier(token: str) -> dict:
    if token not in TOKENS:
        raise ValueError("invalid token")
    return TOKENS[token]


@pytest.fixture
def client():
    server.app.dependency_overrides[get_authenticator] = lambda: FirebaseAuthenticator(
        verifier=_fake_verifier
    )
    yield TestClient(server.app)
    server.app.dependency_overrides.clear()


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


STAGE = {
    "action_type": "FreezeAccount",
    "target_entity_id": "C-1",
    "metadata": {"reason_code": "TEST"},
}


def test_health_is_public(client):
    assert client.get("/health").status_code == 200


def test_missing_token_is_401(client):
    assert client.get("/api/cockpit/workstations/executive").status_code == 401
    assert client.post("/api/cockpit/actions/stage", json=STAGE).status_code == 401


def test_invalid_token_is_401(client):
    assert (
        client.post("/api/cockpit/actions/stage", json=STAGE, headers=_h("nope")).status_code == 401
    )


@pytest.mark.parametrize("token", ["tok-norole", "tok-badrole"])
def test_missing_or_unknown_role_is_403(client, token):
    assert (
        client.post("/api/cockpit/actions/stage", json=STAGE, headers=_h(token)).status_code == 403
    )


def test_identity_comes_from_the_token_not_the_body(client):
    body = {**STAGE, "initiator_officer_id": "SOMEONE_ELSE"}
    resp = client.post("/api/cockpit/actions/stage", json=body, headers=_h("tok-analyst"))
    assert resp.status_code == 200
    token = server.governance.hub.get_status(resp.json()["card"]["intent_id"])
    assert token.requester_agent_id == "u-analyst"


def test_analyst_cannot_approve(client):
    intent = client.post(
        "/api/cockpit/actions/stage", json=STAGE, headers=_h("tok-analyst")
    ).json()["card"]["intent_id"]
    resp = client.post(
        "/api/cockpit/actions/authorize",
        json={"intent_id": intent, "authorizer_id": "ignored"},
        headers=_h("tok-analyst"),
    )
    assert resp.status_code == 403


def test_two_distinct_approvers_commit_and_ids_come_from_tokens(client):
    intent = client.post(
        "/api/cockpit/actions/stage", json=STAGE, headers=_h("tok-analyst")
    ).json()["card"]["intent_id"]
    auth = lambda tok: client.post(  # noqa: E731
        "/api/cockpit/actions/authorize",
        json={"intent_id": intent, "authorizer_id": "forged"},
        headers=_h(tok),
    )
    assert auth("tok-approver-1").json()["status"] == "PENDING_SECOND_EYE"
    assert auth("tok-approver-1").status_code == 400  # the same human cannot approve twice
    assert auth("tok-approver-2").json()["status"] == "COMMITTED"
    approvers = [a.approver_id for a in server.governance.hub.get_status(intent).approvals]
    assert approvers == ["u-approver-1", "u-approver-2"]


def test_an_approver_who_staged_cannot_approve_their_own_action(client):
    intent = client.post(
        "/api/cockpit/actions/stage", json=STAGE, headers=_h("tok-approver-1")
    ).json()["card"]["intent_id"]
    resp = client.post(
        "/api/cockpit/actions/authorize",
        json={"intent_id": intent, "authorizer_id": "x"},
        headers=_h("tok-approver-1"),
    )
    assert resp.status_code == 400
    assert "Four-Eyes" in resp.json()["detail"]


def test_operator_roles_are_closed_set():
    assert Operator(uid="u", email=None, role="analyst").can_stage
    assert not Operator(uid="u", email=None, role="analyst").can_approve
    assert Operator(uid="u", email=None, role="approver").can_approve


def test_deployed_environments_require_firebase_auth(monkeypatch):
    monkeypatch.setenv("EIOS_ENVIRONMENT", "prod-like")
    monkeypatch.delenv("EIOS_AUTH_MODE", raising=False)
    with pytest.raises(RuntimeError, match="EIOS_AUTH_MODE"):
        default_authenticator()


def test_firebase_mode_requires_a_project(monkeypatch):
    monkeypatch.setenv("EIOS_AUTH_MODE", "firebase")
    monkeypatch.delenv("EIOS_FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(RuntimeError, match="project"):
        default_authenticator()


def test_cors_is_never_a_wildcard_when_deployed(monkeypatch):
    monkeypatch.setenv("EIOS_ENVIRONMENT", "stage")
    monkeypatch.delenv("EIOS_CORS_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="EIOS_CORS_ORIGINS"):
        cors_origins()
    monkeypatch.setenv("EIOS_CORS_ORIGINS", "https://app.example.org, https://b.example.org")
    assert cors_origins() == ["https://app.example.org", "https://b.example.org"]
    monkeypatch.setenv("EIOS_CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="wildcard"):
        cors_origins()


def test_dev_mode_keeps_body_identity_for_local_use(monkeypatch):
    monkeypatch.setenv("EIOS_ENVIRONMENT", "dev")
    monkeypatch.delenv("EIOS_AUTH_MODE", raising=False)
    server.app.dependency_overrides.clear()
    resp = TestClient(server.app).post(
        "/api/cockpit/actions/stage", json={**STAGE, "initiator_officer_id": "OFFICER_X"}
    )
    assert resp.status_code == 200
