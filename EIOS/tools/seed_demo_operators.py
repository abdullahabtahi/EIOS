"""Create or update the demo operators in Identity Platform (Identity Toolkit admin API).

Usage: ``uv run python -m tools.seed_demo_operators --project <id> --credentials-file <path>``.
Passwords come from ``EIOS_DEMO_<NAME>_PASSWORD`` or are generated. Generated credentials are written to
an owner-only (0600) file and never printed or committed.
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


def write_credentials(path: str, lines: list[str]) -> None:
    """Write credentials to a new owner-read/write file; refuse to overwrite an existing one."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument(
        "--credentials-file", required=True, help="new file for generated credentials (mode 0600)"
    )
    args = parser.parse_args()

    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session: Any = AuthorizedSession(credentials)  # type: ignore[no-untyped-call]
    session.headers["x-goog-user-project"] = args.project
    credentials_lines: list[str] = []
    for email, role in DEMO_OPERATORS:
        password, generated = _password_for(email)
        uid = ensure_operator(session, args.project, email, password, role)
        if generated:
            credentials_lines.append(f"{email}\t{password}")
        print(f"{role:9} {email}  uid={uid}")
    if credentials_lines:
        write_credentials(args.credentials_file, credentials_lines)
        print(f"generated credentials written to {args.credentials_file} (mode 0600)")


if __name__ == "__main__":
    main()
