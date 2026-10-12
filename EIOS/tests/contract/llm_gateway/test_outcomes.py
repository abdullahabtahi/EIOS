"""T102: every outcome is reachable with the stub provider; the cap and warnings behave."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from eios.llm_gateway.caps import CapEventKind
from eios.llm_gateway.models import Outcome
from eios.llm_gateway.providers.stub import StubFailure, StubProvider
from tests.support.llm_gateway import (
    FixedUsageProvider,
    echo_request,
    make_config,
    make_kit,
)


def test_ok_calls_the_provider_stores_the_result_and_writes_a_trace(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    response = kit.gateway.complete(echo_request())
    assert response.outcome is Outcome.OK
    assert response.content
    assert response.replay_original_at is None
    assert len(kit.provider.calls) == 1
    assert [t["outcome"] for t in kit.traces.records] == ["ok"]
    assert kit.traces.records[0]["trace_id"] == response.trace_id


def test_replay_on_outage_carries_the_original_timestamp(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    first = kit.gateway.complete(echo_request())
    stored_at = kit.clock.instant
    kit.provider.inner = StubProvider(failure=StubFailure.UNAVAILABLE)
    kit.clock.advance(timedelta(hours=2))
    replayed = kit.gateway.complete(echo_request())
    assert replayed.outcome is Outcome.REPLAY
    assert replayed.content == first.content
    assert replayed.replay_original_at == stored_at
    assert replayed.replay_original_at != kit.clock.instant


def test_unavailable_when_provider_fails_and_nothing_is_cached(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, provider=StubProvider(failure=StubFailure.UNAVAILABLE))
    response = kit.gateway.complete(echo_request())
    assert response.outcome is Outcome.UNAVAILABLE
    assert response.content is None
    assert response.replay_original_at is None


def test_cap_reached_without_a_cached_result_never_calls_the_provider(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, config=make_config(daily_token_cap=1))
    assert kit.gateway.complete(echo_request("first")).outcome is Outcome.OK
    response = kit.gateway.complete(echo_request("second"))
    assert response.outcome is Outcome.CAP_REACHED
    assert response.content is None
    assert len(kit.provider.calls) == 1


def test_at_the_cap_a_cached_result_is_replayed_and_the_provider_is_not_called(
    tmp_path: Path,
) -> None:
    kit = make_kit(tmp_path, config=make_config(daily_token_cap=1))
    first = kit.gateway.complete(echo_request("same"))
    kit.clock.advance(timedelta(minutes=1))
    replayed = kit.gateway.complete(echo_request("same"))
    assert replayed.outcome is Outcome.REPLAY
    assert replayed.content == first.content
    assert replayed.replay_original_at == kit.clock.instant - timedelta(minutes=1)
    assert len(kit.provider.calls) == 1


def test_cap_refusals_raise_an_event_and_are_traced(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, config=make_config(daily_token_cap=1))
    kit.gateway.complete(echo_request("first"))
    kit.gateway.complete(echo_request("second"))
    kinds = [e.kind for e in kit.events.events]
    assert CapEventKind.REACHED in kinds
    assert CapEventKind.REFUSED in kinds
    assert [t["outcome"] for t in kit.traces.records] == ["ok", "cap_reached"]


def test_usage_at_50_and_80_percent_returns_ok_with_a_warning_and_does_not_block(
    tmp_path: Path,
) -> None:
    config = make_config(daily_token_cap=100, cap_warning_thresholds_percent=[50, 80])
    kit = make_kit(tmp_path, config=config, provider=FixedUsageProvider(30, 30))
    assert kit.gateway.complete(echo_request("a")).outcome is Outcome.OK  # 60 of 100
    assert [(e.kind, e.threshold_percent) for e in kit.events.events] == [
        (CapEventKind.WARNING, 50)
    ]
    assert kit.gateway.complete(echo_request("b")).outcome is Outcome.OK  # 120 of 100
    kinds = [(e.kind, e.threshold_percent) for e in kit.events.events]
    assert kinds == [
        (CapEventKind.WARNING, 50),
        (CapEventKind.WARNING, 80),
        (CapEventKind.REACHED, 100),
    ]
    assert kit.gateway.complete(echo_request("c")).outcome is Outcome.CAP_REACHED


def test_all_four_outcomes_are_reachable(tmp_path: Path) -> None:
    seen: set[Outcome] = set()
    ok_kit = make_kit(tmp_path / "ok", config=make_config(daily_token_cap=1))
    seen.add(ok_kit.gateway.complete(echo_request("x")).outcome)
    seen.add(ok_kit.gateway.complete(echo_request("x")).outcome)
    seen.add(ok_kit.gateway.complete(echo_request("y")).outcome)
    down = make_kit(tmp_path / "down", provider=StubProvider(failure=StubFailure.TIMEOUT))
    seen.add(down.gateway.complete(echo_request()).outcome)
    assert seen == set(Outcome)
