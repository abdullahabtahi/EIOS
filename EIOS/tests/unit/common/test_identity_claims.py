"""T061 (FR-018): identity comes only from verified claims, never from a request body."""

from __future__ import annotations

import dataclasses
from datetime import timedelta

import pytest

from eios.common.errors import BoundaryValidationError, EiosError
from eios.common.identity_claims import (
    ActorIdentity,
    UnverifiedClaimsError,
    VerifiedClaims,
    claims_from_edge,
    reject_identity_fields,
    resolve_actor,
)
from tests.support.clock import FixedClock

_NOW = FixedClock().now()
_ISSUER = "https://idp.example.test"


def _raw(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "sub": "user-1234",
        "iss": _ISSUER,
        "email": "analyst@example.test",
        "exp": (_NOW + timedelta(minutes=5)).timestamp(),
        "aud": "ignored-claim",
    }
    return {**base, **overrides}


def _claims() -> VerifiedClaims:
    return claims_from_edge(_raw(), edge_verified=True, expected_issuer=_ISSUER, now=_NOW)


def test_verified_claims_are_read_and_frozen() -> None:
    claims = _claims()
    assert claims.subject == "user-1234"
    assert claims.issuer == _ISSUER
    assert claims.email == "analyst@example.test"
    with pytest.raises(dataclasses.FrozenInstanceError):
        claims.subject = "someone-else"  # type: ignore[misc]


def test_email_is_optional() -> None:
    raw = {k: v for k, v in _raw().items() if k != "email"}
    claims = claims_from_edge(raw, edge_verified=True, expected_issuer=_ISSUER, now=_NOW)
    assert claims.email is None


def test_repr_omits_personal_data() -> None:
    assert "analyst@example.test" not in repr(_claims())


def test_claims_not_attested_by_the_edge_are_rejected() -> None:
    with pytest.raises(UnverifiedClaimsError):
        claims_from_edge(_raw(), edge_verified=False, expected_issuer=_ISSUER, now=_NOW)


def test_wrong_issuer_is_rejected_without_echoing_values() -> None:
    with pytest.raises(UnverifiedClaimsError) as info:
        claims_from_edge(
            _raw(iss="https://evil.example.test"),
            edge_verified=True,
            expected_issuer=_ISSUER,
            now=_NOW,
        )
    assert "evil" not in str(info.value)
    assert _ISSUER not in str(info.value)


@pytest.mark.parametrize(
    "override",
    [
        {"sub": ""},
        {"sub": 42},
        {"sub": None},
        {"iss": None},
        {"exp": None},
        {"exp": "tomorrow"},
        {"exp": True},
        {"exp": (_NOW - timedelta(seconds=1)).timestamp()},
        {"exp": _NOW.timestamp()},
        {"email": 7},
    ],
)
def test_malformed_or_expired_claims_are_rejected(override: dict[str, object]) -> None:
    with pytest.raises(UnverifiedClaimsError):
        claims_from_edge(_raw(**override), edge_verified=True, expected_issuer=_ISSUER, now=_NOW)


def test_missing_required_claims_are_rejected() -> None:
    for name in ("sub", "iss", "exp"):
        raw = {k: v for k, v in _raw().items() if k != name}
        with pytest.raises(UnverifiedClaimsError):
            claims_from_edge(raw, edge_verified=True, expected_issuer=_ISSUER, now=_NOW)


def test_non_mapping_claims_are_rejected() -> None:
    with pytest.raises(UnverifiedClaimsError):
        claims_from_edge(
            "not-a-mapping",  # type: ignore[arg-type]
            edge_verified=True,
            expected_issuer=_ISSUER,
            now=_NOW,
        )


def test_unverified_error_is_typed() -> None:
    assert issubclass(UnverifiedClaimsError, EiosError)


def test_claims_cannot_be_built_directly() -> None:
    with pytest.raises(UnverifiedClaimsError):
        VerifiedClaims("user-1", _ISSUER, None, 1.0, object())


def test_actor_comes_from_claims_only() -> None:
    actor = resolve_actor(_claims(), {"note": "approve", "amount": 5})
    assert actor == ActorIdentity(user_id="user-1234", email="analyst@example.test", issuer=_ISSUER)
    with pytest.raises(dataclasses.FrozenInstanceError):
        actor.user_id = "x"  # type: ignore[misc]


@pytest.mark.parametrize("field_name", ["approver", "user", "user_id", "approver_id", "Approver"])
def test_identity_fields_in_a_body_are_rejected(field_name: str) -> None:
    body = {"note": "approve", field_name: "mallory"}
    with pytest.raises(BoundaryValidationError) as info:
        resolve_actor(_claims(), body)
    assert info.value.field_paths == (field_name,)
    assert "mallory" not in str(info.value)


def test_nested_identity_fields_are_rejected_with_their_path() -> None:
    body = {"decision": {"meta": [{"ok": 1}, {"user_id": "mallory"}]}}
    with pytest.raises(BoundaryValidationError) as info:
        reject_identity_fields(body)
    assert info.value.field_paths == ("decision.meta.1.user_id",)


def test_clean_body_passes_and_is_not_mutated() -> None:
    body = {"decision": {"note": "fine"}, "tags": ["a"]}
    reject_identity_fields(body)
    assert body == {"decision": {"note": "fine"}, "tags": ["a"]}


def test_resolve_actor_requires_a_verified_claims_object() -> None:
    with pytest.raises(UnverifiedClaimsError):
        resolve_actor(_raw(), {})  # type: ignore[arg-type]


def test_default_clock_accepts_a_far_future_expiry() -> None:
    raw = _raw(exp=_NOW.timestamp() + 10**9 * 10)
    claims = claims_from_edge(raw, edge_verified=True, expected_issuer=_ISSUER)
    assert claims.subject == "user-1234"


def test_unsafe_parent_keys_are_not_echoed_in_paths() -> None:
    body = {"Bearer-looking Key": {"user": "mallory"}, 7: [{"approver": "m"}]}
    with pytest.raises(BoundaryValidationError) as info:
        reject_identity_fields(body)  # type: ignore[arg-type]
    assert info.value.field_paths == ("<redacted>.user", "7.0.approver")


def test_non_string_keys_are_not_treated_as_identity_fields() -> None:
    reject_identity_fields({1: "a", None: "b"})  # type: ignore[dict-item]


def test_absurdly_deep_bodies_are_rejected() -> None:
    body: dict[str, object] = {"leaf": 1}
    for _ in range(40):
        body = {"n": body}
    with pytest.raises(BoundaryValidationError):
        reject_identity_fields(body)
