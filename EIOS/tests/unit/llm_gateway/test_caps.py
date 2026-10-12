"""Unit tests for the pure cap arithmetic and event model."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from eios.llm_gateway.caps import (
    CapEvent,
    CapEventKind,
    crossing_events,
    is_exhausted,
    refusal_event,
    usage_day,
)

DAY = date(2026, 1, 1)


def _kinds(events: tuple[CapEvent, ...]) -> list[tuple[CapEventKind, int]]:
    return [(e.kind, e.threshold_percent) for e in events]


def test_no_events_when_no_threshold_is_crossed() -> None:
    assert crossing_events(DAY, before=0, after=49, cap=100, thresholds=(50, 80)) == ()


def test_a_threshold_exactly_met_counts_as_crossed() -> None:
    events = crossing_events(DAY, before=0, after=50, cap=100, thresholds=(50, 80))
    assert _kinds(events) == [(CapEventKind.WARNING, 50)]


def test_a_threshold_already_crossed_does_not_fire_again() -> None:
    assert crossing_events(DAY, before=50, after=60, cap=100, thresholds=(50, 80)) == ()


def test_one_call_may_cross_several_thresholds_in_ascending_order() -> None:
    events = crossing_events(DAY, before=10, after=120, cap=100, thresholds=(80, 50))
    assert _kinds(events) == [
        (CapEventKind.WARNING, 50),
        (CapEventKind.WARNING, 80),
        (CapEventKind.REACHED, 100),
    ]


def test_reaching_the_cap_is_reported_once() -> None:
    assert _kinds(crossing_events(DAY, before=99, after=100, cap=100, thresholds=())) == [
        (CapEventKind.REACHED, 100)
    ]
    assert crossing_events(DAY, before=100, after=150, cap=100, thresholds=()) == ()


def test_event_carries_day_usage_and_cap() -> None:
    (event,) = crossing_events(DAY, before=0, after=60, cap=100, thresholds=(50,))
    assert (event.day, event.used_tokens, event.cap_tokens) == (DAY, 60, 100)


def test_thresholds_use_integer_arithmetic_on_awkward_caps() -> None:
    events = crossing_events(DAY, before=0, after=1, cap=3, thresholds=(33, 34))
    assert _kinds(events) == [(CapEventKind.WARNING, 33)]


@pytest.mark.parametrize(("total", "expected"), [(99, False), (100, True), (101, True)])
def test_is_exhausted_at_or_above_the_cap(total: int, expected: bool) -> None:
    assert is_exhausted(total, 100) is expected


def test_refusal_event_reports_the_cap() -> None:
    event = refusal_event(DAY, used=120, cap=100)
    assert (event.kind, event.threshold_percent) == (CapEventKind.REFUSED, 100)


def test_usage_day_is_the_utc_date_whatever_the_clock_zone() -> None:
    late_in_new_york = datetime(2026, 1, 1, 22, 0, tzinfo=timezone(timedelta(hours=-5)))
    assert usage_day(late_in_new_york) == date(2026, 1, 2)
    assert usage_day(datetime(2026, 1, 1, 23, 59, tzinfo=UTC)) == DAY


def test_events_are_frozen() -> None:
    event = refusal_event(DAY, used=1, cap=1)
    with pytest.raises(ValidationError):
        event.used_tokens = 5
