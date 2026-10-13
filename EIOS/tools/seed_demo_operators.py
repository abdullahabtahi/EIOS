"""Create or update the demo operators in Identity Platform (Identity Toolkit admin API).

Usage: ``uv run python -m tools.seed_demo_operators --project <id>``. Passwords come from
``EIOS_DEMO_<NAME>_PASSWORD`` or are generated and printed once. Credentials are never committed.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
from typing import Any, Protocol

from eios.cockpit.auth import ALL_ROLES

API = "https://identitytoolkit.googleapis.com/v1"

# (email, role). The reserved example.org domain cannot collide with a real mailbox.
DEMO_OPERATORS: tuple[tuple[str, str], ...] = (
    ("analyst@eios-demo.example.org", "analyst"),
    ("approver1@eios-demo.example.org", "approver"),
    ("approver2@eios-demo.example.org", "approver"),
)


class _Session(Protocol):
    def post(self, url: str, json: dict[str, Any], **kwargs: Any) -> Any: ...


def role_claims(role: str) -> str:
    return json.dumps({"role": role}, separators=(",", ":"))


def ensure_operator(session: _Session, project: str, email: str, password: str, role: str) -> str:
    """Create the operator if absent, then set its password and role claim. Returns the uid."""
    if role not in ALL_ROLES:
        raise ValueError(f"unknown role '{role}'")
    lookup = session.post(f"{API}/projects/{project}/accounts:lookup", json={"email": [email]})
    lookup.raise_for_status()
    users = lookup.json().get("users")
    if users:
        uid = users[0]["localId"]
    else:
        created = session.post(
            f"{API}/accounts:signUp",
            json={"email": email, "password": password, "targetProjectId": project},
        )
        created.raise_for_status()
        uid = created.json()["localId"]
    update = session.post(
        f"{API}/accounts:update",
        json={
            "localId": uid,
            "password": password,
            "customAttributes": role_claims(role),
            "targetProjectId": project,
        },
    )
    update.raise_for_status()
    return str(uid)


def _password_for(email: str) -> tuple[str, bool]:
    name = email.split("@")[0].upper()
    configured = os.environ.get(f"EIOS_DEMO_{name}_PASSWORD")
    return (configured, False) if configured else (secrets.token_urlsafe(16), True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session: Any = AuthorizedSession(credentials)  # type: ignore[no-untyped-call]
    session.headers["x-goog-user-project"] = args.project
    for email, role in DEMO_OPERATORS:
        password, generated = _password_for(email)
        uid = ensure_operator(session, args.project, email, password, role)
        shown = password if generated else "(from environment)"
        print(f"{role:9} {email}  uid={uid}  password={shown}")  # noqa: T201 - one-time operator output


if __name__ == "__main__":
    main()
