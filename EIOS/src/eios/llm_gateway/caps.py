"""Daily token cap arithmetic and cap events (FR-023).

The cap day is the UTC date. Warning thresholds are percentages below 100 from configuration
(``[TARGET]`` values); crossing detection compares the running total before and after a call,
so each threshold fires once per day even with concurrent callers (the counter is atomic).
A call that starts below the cap may finish above it: overshoot by one call is accepted
(``[ASSUMPTION]``: token usage is only known after the provider answers).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Protocol

from eios.common.validation import StrictModel
from eios.llm_gateway.models import Count

FULL_PERCENT = 100


class CapEventKind(StrEnum):
    WARNING = "warning"
    REACHED = "reached"
    REFUSED = "refused"


class CapEvent(StrictModel):
    kind: CapEventKind
    threshold_percent: int
    day: date
    used_tokens: Count
    cap_tokens: Count


class CounterStore(Protocol):
    """Atomic per-day token counter."""

    def add_tokens(self, day: date, count: int) -> int:
        """Add ``count`` (>= 0) to the day's total and return the new running total."""
        ...


class EventSink(Protocol):
    def emit(self, event: CapEvent) -> None: ...


def usage_day(now: datetime) -> date:
    """The cap day for a moment: its UTC date."""
    return now.astimezone(UTC).date()


def is_exhausted(total: int, cap: int) -> bool:
    return total >= cap


def _event(kind: CapEventKind, percent: int, day: date, used: int, cap: int) -> CapEvent:
    return CapEvent(kind=kind, threshold_percent=percent, day=day, used_tokens=used, cap_tokens=cap)


def crossing_events(
    day: date, *, before: int, after: int, cap: int, thresholds: Iterable[int]
) -> tuple[CapEvent, ...]:
    """Events for the thresholds (and the cap itself) crossed when usage moved before -> after."""
    events = [
        _event(CapEventKind.WARNING, percent, day, after, cap)
        for percent in sorted(thresholds)
        if before * FULL_PERCENT < percent * cap <= after * FULL_PERCENT
    ]
    if before < cap <= after:
        events.append(_event(CapEventKind.REACHED, FULL_PERCENT, day, after, cap))
    return tuple(events)


def refusal_event(day: date, *, used: int, cap: int) -> CapEvent:
    """Event for a call refused because the cap was already reached."""
    return _event(CapEventKind.REFUSED, FULL_PERCENT, day, used, cap)
