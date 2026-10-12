"""T105 (FR-023): the daily cap blocks at 100% without calling the provider; replays still work."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from eios.llm_gateway.caps import CapEventKind
from eios.llm_gateway.models import Outcome
from tests.support.llm_gateway import FixedUsageProvider, echo_request, make_config, make_kit


def _kit(tmp_path: Path, *, cap: int = 100, per_call: int = 30):  # type: ignore[no-untyped-def]
    config = make_config(daily_token_cap=cap, cap_warning_thresholds_percent=[50, 80])
    return make_kit(tmp_path, config=config, provider=FixedUsageProvider(per_call, per_call))


def test_calls_are_allowed_until_usage_reaches_the_cap(tmp_path: Path) -> None:
    kit = _kit(tmp_path)
    assert kit.gateway.complete(echo_request("a")).outcome is Outcome.OK  # 60
    assert kit.gateway.complete(echo_request("b")).outcome is Outcome.OK  # 120, overshoot allowed
    assert kit.gateway.complete(echo_request("c")).outcome is Outcome.CAP_REACHED
    assert len(kit.provider.calls) == 2


def test_usage_exactly_at_the_cap_blocks_the_next_call(tmp_path: Path) -> None:
    kit = _kit(tmp_path, cap=60)
    assert kit.gateway.complete(echo_request("a")).outcome is Outcome.OK  # exactly 60
    assert kit.gateway.complete(echo_request("b")).outcome is Outcome.CAP_REACHED
    assert len(kit.provider.calls) == 1


def test_the_provider_is_never_called_after_the_cap_is_reached(tmp_path: Path) -> None:
    kit = _kit(tmp_path, cap=1)
    kit.gateway.complete(echo_request("a"))
    for n in range(5):
        kit.gateway.complete(echo_request(f"new-{n}"))
    assert len(kit.provider.calls) == 1


def test_refused_calls_consume_no_tokens_and_report_none(tmp_path: Path) -> None:
    kit = _kit(tmp_path, cap=1)
    kit.gateway.complete(echo_request("a"))
    before = kit.counter.add_tokens(kit.clock.instant.date(), 0)
    kit.gateway.complete(echo_request("b"))
    assert kit.counter.add_tokens(kit.clock.instant.date(), 0) == before
    trace = kit.traces.records[-1]
    assert trace["outcome"] == "cap_reached"
    assert (trace["tokens_in"], trace["tokens_out"]) == (0, 0)


def test_warning_events_fire_once_per_threshold_and_do_not_block(tmp_path: Path) -> None:
    kit = _kit(tmp_path, cap=1000, per_call=300)  # 600 per call
    assert kit.gateway.complete(echo_request("a")).outcome is Outcome.OK  # 60%: one warning
    assert kit.gateway.complete(echo_request("b")).outcome is Outcome.OK  # 120%: an 80% warning
    warnings = [e for e in kit.events.events if e.kind is CapEventKind.WARNING]
    assert [w.threshold_percent for w in warnings] == [50, 80]


def test_cap_reached_event_fires_exactly_once(tmp_path: Path) -> None:
    kit = _kit(tmp_path, cap=1)
    for n in range(4):
        kit.gateway.complete(echo_request(f"r{n}"))
    reached = [e for e in kit.events.events if e.kind is CapEventKind.REACHED]
    refused = [e for e in kit.events.events if e.kind is CapEventKind.REFUSED]
    assert len(reached) == 1
    assert len(refused) == 3


def test_a_cached_result_is_replayed_at_the_cap_without_a_provider_call(tmp_path: Path) -> None:
    kit = _kit(tmp_path, cap=1)
    first = kit.gateway.complete(echo_request("same"))
    calls = len(kit.provider.calls)
    again = kit.gateway.complete(echo_request("same"))
    assert (again.outcome, again.content) == (Outcome.REPLAY, first.content)
    assert again.replay_original_at is not None
    assert len(kit.provider.calls) == calls
    assert kit.traces.records[-1]["outcome"] == "replay"


def test_no_cached_result_at_the_cap_is_an_explicit_refusal(tmp_path: Path) -> None:
    kit = _kit(tmp_path, cap=1)
    kit.gateway.complete(echo_request("one"))
    refused = kit.gateway.complete(echo_request("two"))
    assert refused.outcome is Outcome.CAP_REACHED
    assert refused.content is None
    assert refused.replay_original_at is None


def test_the_counter_resets_on_the_next_utc_day(tmp_path: Path) -> None:
    kit = _kit(tmp_path, cap=1)
    kit.gateway.complete(echo_request("one"))
    assert kit.gateway.complete(echo_request("two")).outcome is Outcome.CAP_REACHED
    kit.clock.advance(timedelta(days=1))
    assert kit.gateway.complete(echo_request("two")).outcome is Outcome.OK


def test_warning_thresholds_come_from_configuration(tmp_path: Path) -> None:
    config = make_config(daily_token_cap=100, cap_warning_thresholds_percent=[10])
    kit = make_kit(tmp_path, config=config, provider=FixedUsageProvider(6, 6))
    kit.gateway.complete(echo_request("a"))
    assert [e.threshold_percent for e in kit.events.events] == [10]
