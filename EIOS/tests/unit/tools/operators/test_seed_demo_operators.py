"""The demo-operator seeder builds the right Identity Toolkit requests and never invents roles."""

import json

import pytest

from tools.seed_demo_operators import (
    DEMO_OPERATORS,
    ensure_operator,
    role_claims,
    write_credentials,
)


class FakeSession:
    """Records Identity Toolkit calls; ``existing`` maps email -> localId."""

    def __init__(self, existing: dict[str, str] | None = None) -> None:
        self.existing = existing or {}
        self.calls: list[tuple[str, dict]] = []

    def post(self, url: str, json: dict, **_: object):
        self.calls.append((url.rsplit("/", 1)[-1], json))

        class Response:
            status_code = 200

            def __init__(self, payload: dict) -> None:
                self._payload = payload

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return self._payload

        if url.endswith("accounts:lookup"):
            email = json["email"][0]
            return Response(
                {"users": [{"localId": self.existing[email]}]} if email in self.existing else {}
            )
        if url.endswith("accounts:signUp"):
            return Response({"localId": "new-uid"})
        return Response({})


def test_role_claims_is_json_with_only_the_role() -> None:
    assert json.loads(role_claims("approver")) == {"role": "approver"}


def test_demo_roles_are_all_recognised() -> None:
    from eios.cockpit.auth import ALL_ROLES

    assert {role for _, role in DEMO_OPERATORS} <= ALL_ROLES
    assert {"analyst", "approver"} <= {role for _, role in DEMO_OPERATORS}


def test_a_new_operator_is_created_then_given_its_role() -> None:
    session = FakeSession()
    uid = ensure_operator(session, "p", "a@example.org", "pw-1", "analyst")
    assert uid == "new-uid"
    assert [name for name, _ in session.calls] == [
        "accounts:lookup",
        "accounts:signUp",
        "accounts:update",
    ]
    update = session.calls[-1][1]
    assert update["localId"] == "new-uid"
    assert json.loads(update["customAttributes"]) == {"role": "analyst"}


def test_an_existing_operator_is_updated_not_recreated() -> None:
    session = FakeSession({"a@example.org": "uid-9"})
    assert ensure_operator(session, "p", "a@example.org", "pw-2", "approver") == "uid-9"
    assert "accounts:signUp" not in [name for name, _ in session.calls]
    assert session.calls[-1][1]["password"] == "pw-2"


def test_unknown_roles_are_refused() -> None:
    with pytest.raises(ValueError, match="role"):
        ensure_operator(FakeSession(), "p", "a@example.org", "pw", "superuser")


def test_credentials_file_is_owner_only_and_never_overwritten(tmp_path) -> None:
    import os
    import stat

    path = str(tmp_path / "creds.txt")
    write_credentials(path, ["a@example.org\tpw"])
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    with pytest.raises(FileExistsError):
        write_credentials(path, ["other"])
