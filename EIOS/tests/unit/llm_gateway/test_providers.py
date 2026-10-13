"""T112 (FR-026, FR-027): the stub is deterministic; provider output is untrusted and validated."""

from __future__ import annotations

import dataclasses

import pytest

from eios.llm_gateway.providers.base import (
    Provider,
    ProviderOutputInvalid,
    ProviderResult,
    ProviderTimeout,
    ProviderUnavailable,
    parse_provider_result,
)
from eios.llm_gateway.providers.stub import StubFailure, StubProvider
from tests.support.secret_shapes import api_key

LIMITS = {"requests_per_minute": 60}


def test_stub_satisfies_the_provider_protocol() -> None:
    assert isinstance(StubProvider(), Provider)


def test_stub_is_deterministic() -> None:
    stub = StubProvider()
    first = stub.generate("prompt text here", None, LIMITS)
    assert first == stub.generate("prompt text here", None, LIMITS)
    assert first != stub.generate("another prompt", None, LIMITS)


def test_stub_returns_canned_response_for_a_known_prompt() -> None:
    stub = StubProvider(canned={"known prompt": "canned answer"})
    result = stub.generate("known prompt", "any-model", LIMITS)
    assert result.content == "canned answer"
    assert result.tokens_in == 2
    assert result.tokens_out == 2


def test_stub_counts_tokens_deterministically() -> None:
    result = StubProvider(canned={"a b c": "x y"}).generate("a b c", None, LIMITS)
    assert (result.tokens_in, result.tokens_out) == (3, 2)


def test_stub_failure_is_configurable_and_immutable() -> None:
    healthy = StubProvider()
    failing = healthy.with_failure(StubFailure.UNAVAILABLE)
    assert failing is not healthy
    assert healthy.failure is StubFailure.NONE
    assert healthy.generate("p", None, LIMITS).content
    with pytest.raises(ProviderUnavailable):
        failing.generate("p", None, LIMITS)


def test_stub_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        StubProvider().failure = StubFailure.TIMEOUT  # type: ignore[misc]


def test_with_canned_adds_without_changing_the_original() -> None:
    base = StubProvider()
    extended = base.with_canned("q", "a")
    assert extended.generate("q", None, LIMITS).content == "a"
    assert base.generate("q", None, LIMITS).content != "a"


def test_timeout_is_a_kind_of_unavailable() -> None:
    assert issubclass(ProviderTimeout, ProviderUnavailable)
    with pytest.raises(ProviderUnavailable):
        StubProvider(failure=StubFailure.TIMEOUT).generate("p", None, LIMITS)
    with pytest.raises(ProviderTimeout):
        StubProvider(failure=StubFailure.TIMEOUT).generate("p", None, LIMITS)


def test_malformed_output_raises_a_typed_error_and_returns_nothing() -> None:
    stub = StubProvider(failure=StubFailure.MALFORMED)
    with pytest.raises(ProviderOutputInvalid):
        stub.generate("p", None, LIMITS)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "just a string",
        {"content": "x"},
        {"content": 5, "tokens_in": 1, "tokens_out": 1},
        {"content": "x", "tokens_in": -1, "tokens_out": 1},
        {"content": "x", "tokens_in": 1.5, "tokens_out": 1},
        {"content": "x", "tokens_in": "1", "tokens_out": 1},
        {"content": "x", "tokens_in": 1, "tokens_out": 1, "extra": "field"},
    ],
)
def test_parse_provider_result_rejects_invalid_payloads(raw: object) -> None:
    with pytest.raises(ProviderOutputInvalid):
        parse_provider_result(raw)


def test_parse_accepts_valid_payload_and_provider_result() -> None:
    raw = {"content": "x", "tokens_in": 1, "tokens_out": 2}
    parsed = parse_provider_result(raw)
    assert parsed == ProviderResult(content="x", tokens_in=1, tokens_out=2)
    assert parse_provider_result(parsed) == parsed


def test_validation_error_never_echoes_provider_output() -> None:
    secret = api_key()
    with pytest.raises(ProviderOutputInvalid) as caught:
        parse_provider_result({"content": secret, "tokens_in": "bad", "tokens_out": 1})
    assert secret not in str(caught.value)


def test_provider_result_is_frozen() -> None:
    result = ProviderResult(content="x", tokens_in=0, tokens_out=0)
    with pytest.raises(ValueError):
        result.content = "y"
