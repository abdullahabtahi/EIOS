"""T104 (FR-024, FR-025): outages degrade to a replay or an explicit unavailable."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import pytest

from eios.llm_gateway.models import Outcome
from eios.llm_gateway.providers.base import ProviderUnavailable
from eios.llm_gateway.providers.stub import StubFailure, StubProvider
from tests.support.llm_gateway import echo_request, make_kit
from tests.support.secret_shapes import api_key

FAILURES = [StubFailure.UNAVAILABLE, StubFailure.TIMEOUT, StubFailure.MALFORMED]


@pytest.mark.parametrize("failure", FAILURES)
def test_empty_store_and_failing_provider_returns_unavailable_never_text(
    tmp_path: Path, failure: StubFailure
) -> None:
    kit = make_kit(tmp_path, provider=StubProvider(failure=failure))
    response = kit.gateway.complete(echo_request())
    assert response.outcome is Outcome.UNAVAILABLE
    assert response.content is None
    assert response.replay_original_at is None
    assert response.trace_id


@pytest.mark.parametrize("failure", FAILURES)
def test_failing_provider_with_a_cached_result_replays_it(
    tmp_path: Path, failure: StubFailure
) -> None:
    kit = make_kit(tmp_path)
    first = kit.gateway.complete(echo_request())
    kit.clock.advance(timedelta(minutes=3))
    kit.provider.inner = StubProvider(failure=failure)
    again = kit.gateway.complete(echo_request())
    assert again.outcome is Outcome.REPLAY
    assert again.content == first.content
    assert again.replay_original_at is not None
    assert again.replay_original_at < kit.clock.instant


def test_a_different_request_does_not_get_another_requests_cached_text(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    kit.gateway.complete(echo_request("one"))
    kit.provider.inner = StubProvider(failure=StubFailure.UNAVAILABLE)
    other = kit.gateway.complete(echo_request("two"))
    assert other.outcome is Outcome.UNAVAILABLE
    assert other.content is None


def test_a_failed_call_stores_nothing_and_reports_no_tokens(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, provider=StubProvider(failure=StubFailure.MALFORMED))
    kit.gateway.complete(echo_request())
    kit.provider.inner = StubProvider()
    assert kit.counter.add_tokens(kit.clock.instant.date(), 0) == 0
    trace = kit.traces.records[0]
    assert (trace["tokens_in"], trace["tokens_out"]) == (0, 0)


def test_replay_does_not_consume_cap_tokens(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    kit.gateway.complete(echo_request())
    used = kit.counter.add_tokens(kit.clock.instant.date(), 0)
    kit.provider.inner = StubProvider(failure=StubFailure.UNAVAILABLE)
    kit.gateway.complete(echo_request())
    assert kit.counter.add_tokens(kit.clock.instant.date(), 0) == used


def test_provider_error_text_never_reaches_the_response_trace_or_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    secret = api_key()

    class Leaky:
        def generate(self, rendered_prompt: str, model_id: str | None, limits: object):  # type: ignore[no-untyped-def]
            raise ProviderUnavailable(f"upstream said: key={secret}")

    kit = make_kit(tmp_path, provider=Leaky())
    with caplog.at_level(logging.DEBUG, logger="eios.llm_gateway"):
        response = kit.gateway.complete(echo_request())
    assert response.outcome is Outcome.UNAVAILABLE
    assert secret not in caplog.text
    assert secret not in repr(kit.traces.records)
    assert "ProviderUnavailable" in caplog.text  # the failure is logged, not swallowed


def test_unexpected_provider_errors_are_not_swallowed(tmp_path: Path) -> None:
    class Broken:
        def generate(self, rendered_prompt: str, model_id: str | None, limits: object):  # type: ignore[no-untyped-def]
            raise RuntimeError("programming error")

    kit = make_kit(tmp_path, provider=Broken())
    with pytest.raises(RuntimeError):
        kit.gateway.complete(echo_request())
