"""Verified identity claims (FR-018): who acted comes from the identity provider, not the body.

Public API:
- ``claims_from_edge(raw, *, edge_verified, expected_issuer, now=None) -> VerifiedClaims``: the only
  way to obtain claims; raises ``UnverifiedClaimsError`` unless the platform edge attested the token
  and ``sub``, ``iss`` (must equal ``expected_issuer``) and an unexpired ``exp`` (epoch seconds)
  are present and well formed.
- ``resolve_actor(claims, body) -> ActorIdentity``: the identity to record for a request. Rejects a
  body carrying ``approver``, ``user`` or ``user_id`` (any case or separator, at any depth).
- ``reject_identity_fields(body)``: just the body guard, raises ``BoundaryValidationError``.
- ``VerifiedClaims`` / ``ActorIdentity``: frozen values. ``UnverifiedClaimsError``: typed failure.

F00 ships no identity provider (research R-13): the edge validates the token and passes the claims
mapping plus an attestation flag. ``VerifiedClaims`` refuses direct construction; that is a type
discipline for callers, not a security boundary. Error messages never echo claim or body values.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from eios.common.errors import BoundaryValidationError, EiosError

_MAX_BODY_DEPTH = 32
# Compared after casefolding and removing "_" and "-": approver, approverid, user, userid.
_FORBIDDEN_BODY_KEYS = frozenset({"approver", "approverid", "user", "userid"})
_SAFE_SEGMENT = re.compile(r"[a-z_][a-z0-9_]{0,63}")
_REDACTED_SEGMENT = "<redacted>"
_ATTESTATION = object()


class UnverifiedClaimsError(EiosError):
    """Claims are not attested, malformed, from the wrong issuer, or expired."""


@dataclass(frozen=True, slots=True)
class VerifiedClaims:
    """Claims the edge verified; build with ``claims_from_edge``, never directly."""

    subject: str
    issuer: str
    email: str | None = field(repr=False)
    expires_at: float
    _attestation: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._attestation is not _ATTESTATION:
            raise UnverifiedClaimsError("claims must come from claims_from_edge()")


@dataclass(frozen=True, slots=True)
class ActorIdentity:
    """The identity recorded against an action; derived from verified claims only."""

    user_id: str
    email: str | None = field(repr=False)
    issuer: str


def _reject(reason: str) -> UnverifiedClaimsError:
    return UnverifiedClaimsError(f"claims rejected: {reason}")


def _required_str(raw: Mapping[str, object], claim: str) -> str:
    value = raw.get(claim)
    if not isinstance(value, str) or not value:
        raise _reject(f"claim '{claim}' is missing or malformed")
    return value


def _expiry(raw: Mapping[str, object], now: datetime) -> float:
    exp = raw.get("exp")
    if isinstance(exp, bool) or not isinstance(exp, int | float):
        raise _reject("claim 'exp' is missing or malformed")
    if exp <= now.timestamp():
        raise _reject("claims are expired")
    return float(exp)


def _optional_email(raw: Mapping[str, object]) -> str | None:
    email = raw.get("email")
    if email is not None and not isinstance(email, str):
        raise _reject("claim 'email' is malformed")
    return email


def claims_from_edge(
    raw: Mapping[str, object],
    *,
    edge_verified: bool,
    expected_issuer: str,
    now: datetime | None = None,
) -> VerifiedClaims:
    """Build ``VerifiedClaims`` from a claims mapping the platform edge has already validated."""
    if edge_verified is not True:
        raise _reject("not attested as verified by the platform edge")
    if not isinstance(raw, Mapping):
        raise _reject("claims must be a mapping")
    subject = _required_str(raw, "sub")
    issuer = _required_str(raw, "iss")
    if issuer != expected_issuer:
        raise _reject("issuer is not the expected issuer")
    expires_at = _expiry(raw, now if now is not None else datetime.now(UTC))
    return VerifiedClaims(subject, issuer, _optional_email(raw), expires_at, _ATTESTATION)


def _segment(part: object) -> str:
    if isinstance(part, int):
        return str(part)
    return part if isinstance(part, str) and _SAFE_SEGMENT.fullmatch(part) else _REDACTED_SEGMENT


def _is_identity_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    return key.casefold().replace("_", "").replace("-", "") in _FORBIDDEN_BODY_KEYS


def _find_identity_fields(value: object, path: tuple[str, ...], depth: int) -> list[str]:
    if depth > _MAX_BODY_DEPTH:
        raise BoundaryValidationError("request body is nested too deeply", (".".join(path),))
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _is_identity_key(key):
                found.append(".".join((*path, str(key))))
            else:
                found.extend(_find_identity_fields(item, (*path, _segment(key)), depth + 1))
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            found.extend(_find_identity_fields(item, (*path, str(index)), depth + 1))
    return found


def reject_identity_fields(body: Mapping[str, object]) -> None:
    """Raise BoundaryValidationError if the body carries approver or user identity fields."""
    paths = _find_identity_fields(body, (), 0)
    if paths:
        raise BoundaryValidationError(
            "request body must not carry identity; identity comes from verified claims only",
            tuple(paths),
        )


def resolve_actor(claims: VerifiedClaims, body: Mapping[str, object]) -> ActorIdentity:
    """Return the actor to record: from ``claims`` only, after rejecting identity in ``body``."""
    if not isinstance(claims, VerifiedClaims):
        raise UnverifiedClaimsError("identity requires a VerifiedClaims object")
    reject_identity_fields(body)
    return ActorIdentity(user_id=claims.subject, email=claims.email, issuer=claims.issuer)
