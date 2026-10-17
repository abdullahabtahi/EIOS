"""Operator authentication and role-based access for the cockpit API.

Deployed environments verify Firebase (Identity Platform) ID tokens; the operator's identity and
role come from the verified token, never from the request body. A trusted-anonymous dev mode
exists only for local use and refuses to start anywhere else.
"""

from __future__ import annotations

import functools
import os
from collections.abc import Callable
from typing import Any, Protocol

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

LOCAL_ENVIRONMENTS = frozenset({"dev", "test"})
AUTH_MODE_ENV = "EIOS_AUTH_MODE"
ENVIRONMENT_ENV = "EIOS_ENVIRONMENT"
CORS_ENV = "EIOS_CORS_ORIGINS"
DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3012",
    "http://127.0.0.1:3012",
]

# Closed set of roles, carried in the Firebase custom claim `role`.
STAGE_ROLES = frozenset({"analyst", "approver", "compliance_head"})
APPROVE_ROLES = frozenset({"approver", "compliance_head"})
ALL_ROLES = STAGE_ROLES | APPROVE_ROLES


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class Operator(BaseModel):
    model_config = ConfigDict(frozen=True)

    uid: str
    email: str | None
    role: str

    @property
    def can_stage(self) -> bool:
        return self.role in STAGE_ROLES

    @property
    def can_approve(self) -> bool:
        return self.role in APPROVE_ROLES


class Authenticator(Protocol):
    def authenticate(self, token: str | None) -> Operator | None:
        """Return the operator, None for trusted-anonymous dev, or raise AuthError."""
        ...


class DevAuthenticator:
    """Trusted-anonymous access for local development. Never constructed outside dev/test."""

    def authenticate(self, token: str | None) -> Operator | None:
        return None


class FirebaseAuthenticator:
    """Verifies Firebase ID tokens (RS256, issuer and audience bound to the project)."""

    def __init__(
        self, project_id: str | None = None, verifier: Callable[[str], dict[str, Any]] | None = None
    ) -> None:
        if verifier is None:
            if not project_id:
                raise RuntimeError("Firebase auth needs a project id (EIOS_FIREBASE_PROJECT_ID)")
            verifier = _firebase_verifier(project_id)
        self._verify = verifier

    def authenticate(self, token: str | None) -> Operator:
        if not token:
            raise AuthError(status.HTTP_401_UNAUTHORIZED, "Authentication required")
        try:
            claims = self._verify(token)
        except Exception as exc:
            raise AuthError(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
        role = claims.get("role")
        if role not in ALL_ROLES:
            raise AuthError(status.HTTP_403_FORBIDDEN, "Operator has no recognised role")
        return Operator(uid=str(claims["sub"]), email=claims.get("email"), role=str(role))


def _firebase_verifier(project_id: str) -> Callable[[str], dict[str, Any]]:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    request = google_requests.Request()

    def verify(token: str) -> dict[str, Any]:
        claims: dict[str, Any] = id_token.verify_firebase_token(token, request, audience=project_id)
        return claims

    return verify


def default_authenticator() -> Authenticator:
    environment = os.getenv(ENVIRONMENT_ENV, "dev")
    mode = os.getenv(AUTH_MODE_ENV, "")
    if mode == "firebase":
        project_id = os.getenv("EIOS_FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise RuntimeError(
                "Firebase auth needs a project id: set EIOS_FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT"
            )
        return FirebaseAuthenticator(project_id)
    if mode in ("", "dev"):
        if environment in LOCAL_ENVIRONMENTS:
            return DevAuthenticator()
        raise RuntimeError(
            f"{AUTH_MODE_ENV}=firebase must be set in the '{environment}' environment; "
            "refusing to serve the cockpit unauthenticated"
        )
    raise RuntimeError(f"Unknown {AUTH_MODE_ENV} '{mode}'")


def cors_origins() -> list[str]:
    environment = os.getenv(ENVIRONMENT_ENV, "dev")
    raw = os.getenv(CORS_ENV)
    if raw:
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        if "*" in origins:
            raise RuntimeError(f"{CORS_ENV} must list explicit origins, not a wildcard")
        return origins
    if environment in LOCAL_ENVIRONMENTS:
        return list(DEV_CORS_ORIGINS)
    raise RuntimeError(f"{CORS_ENV} must be set in the '{environment}' environment")


@functools.lru_cache(maxsize=1)
def get_authenticator() -> Authenticator:
    return default_authenticator()


_bearer = HTTPBearer(auto_error=False)


def current_operator(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    authenticator: Authenticator = Depends(get_authenticator),
) -> Operator | None:
    """The authenticated operator, or None in trusted-anonymous dev mode. Raises 401/403 otherwise."""
    try:
        return authenticator.authenticate(credentials.credentials if credentials else None)
    except AuthError as exc:
        headers = (
            {"WWW-Authenticate": "Bearer"}
            if exc.status_code == status.HTTP_401_UNAUTHORIZED
            else None
        )
        raise HTTPException(
            status_code=exc.status_code, detail=exc.detail, headers=headers
        ) from exc


def require_roles(allowed: frozenset[str]) -> Callable[[Operator | None], Operator | None]:
    """Dependency enforcing that an authenticated operator holds one of ``allowed`` roles."""

    def check(operator: Operator | None = Depends(current_operator)) -> Operator | None:
        if operator is not None and operator.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operator role is not permitted for this action",
            )
        return operator

    return check
