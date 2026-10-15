"""Create or update the demo operators in Identity Platform (Identity Toolkit admin API).

Usage: ``uv run python -m tools.seed_demo_operators --project <id> --credentials-file <path>``.
Passwords come from ``EIOS_DEMO_<NAME>_PASSWORD`` or are generated. Generated credentials are written to
an owner-only (0600) file and never printed or committed.

Two optional groups, for a hackathon review:
- ``--reviewers`` adds three accounts for reviewers and judges (an analyst and two approvers, so the four-eyes
  flow can be shown end to end). They share one password, read from ``EIOS_REVIEWER_PASSWORD`` (at least 12
  characters) because it is meant to be shown on the login page; it never goes in a file or in git.
- ``--owner-email you@example.com`` authorises one real mailbox as a ``compliance_head``, with a generated password
  (or ``EIOS_OWNER_PASSWORD``) written to the credentials file.
``--skip-demo-operators`` leaves the three standard accounts alone, so their passwords are not reset.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from eios.cockpit.auth import ALL_ROLES

API = "https://identitytoolkit.googleapis.com/v1"

# (email, role). The reserved example.org domain cannot collide with a real mailbox.
DEMO_OPERATORS: tuple[tuple[str, str], ...] = (
    ("analyst@eios-demo.example.org", "analyst"),
    ("approver1@eios-demo.example.org", "approver"),
    ("approver2@eios-demo.example.org", "approver"),
)


# The reviewers and judges: one analyst and two approvers (four-eyes needs two different people). The shared password
# is intended to be public (it is shown on the login page), so these accounts hold nothing but the demo's synthetic data.
REVIEWER_OPERATORS: tuple[tuple[str, str], ...] = (
    ("judge-analyst@eios-demo.example.org", "analyst"),
    ("judge-approver1@eios-demo.example.org", "approver"),
    ("judge-approver2@eios-demo.example.org", "approver"),
)
REVIEWER_PASSWORD_ENV = "EIOS_REVIEWER_PASSWORD"  # noqa: S105 - the name of a variable, not a password
OWNER_PASSWORD_ENV = "EIOS_OWNER_PASSWORD"  # noqa: S105
OWNER_ROLE = "compliance_head"
MIN_SHARED_PASSWORD_CHARS = 12
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class PlannedOperator:
    email: str
    role: str
    password: str
    generated: (
        bool  # True when the password was invented here and must be written to the credentials file
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


def planned_operators(
    *,
    include_demo: bool = True,
    reviewers: bool = False,
    owner_email: str | None = None,
    env: Mapping[str, str] | None = None,
) -> list[PlannedOperator]:
    """Who to create or update, with passwords resolved. Pure: nothing is sent anywhere."""
    source = os.environ if env is None else env
    plan: list[PlannedOperator] = []
    if include_demo:
        for email, role in DEMO_OPERATORS:
            name = email.split("@")[0].upper()
            configured = source.get(f"EIOS_DEMO_{name}_PASSWORD")
            plan.append(
                PlannedOperator(
                    email, role, configured or secrets.token_urlsafe(16), not configured
                )
            )
    if reviewers:
        shared = (source.get(REVIEWER_PASSWORD_ENV) or "").strip()
        if len(shared) < MIN_SHARED_PASSWORD_CHARS:
            raise ValueError(
                f"{REVIEWER_PASSWORD_ENV} must be set to at least {MIN_SHARED_PASSWORD_CHARS} characters"
            )
        plan.extend(
            PlannedOperator(email, role, shared, False) for email, role in REVIEWER_OPERATORS
        )
    if owner_email:
        owner = owner_email.strip().lower()
        if not _EMAIL.match(owner):
            raise ValueError(f"'{owner_email}' is not an email address")
        configured = (source.get(OWNER_PASSWORD_ENV) or "").strip()
        plan.append(
            PlannedOperator(
                owner, OWNER_ROLE, configured or secrets.token_urlsafe(16), not configured
            )
        )
    return plan


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
    parser.add_argument(
        "--reviewers", action="store_true", help="add the shared reviewer and judge accounts"
    )
    parser.add_argument("--owner-email", help="authorise this mailbox as a compliance_head")
    parser.add_argument(
        "--skip-demo-operators",
        action="store_true",
        help="leave the three standard accounts untouched",
    )
    args = parser.parse_args()
    plan = planned_operators(
        include_demo=not args.skip_demo_operators,
        reviewers=args.reviewers,
        owner_email=args.owner_email,
    )

    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session: Any = AuthorizedSession(credentials)  # type: ignore[no-untyped-call]
    session.headers["x-goog-user-project"] = args.project
    credentials_lines: list[str] = []
    for operator in plan:
        uid = ensure_operator(
            session, args.project, operator.email, operator.password, operator.role
        )
        if operator.generated:
            credentials_lines.append(f"{operator.email}\t{operator.password}")
        print(f"{operator.role:15} {operator.email}  uid={uid}")
    if credentials_lines:
        write_credentials(args.credentials_file, credentials_lines)
        print(f"generated credentials written to {args.credentials_file} (mode 0600)")


if __name__ == "__main__":
    main()
