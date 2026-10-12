"""A fixed clock so time-dependent behaviour is deterministic in tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class FixedClock:
    instant: datetime = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.instant

    def advanced(self, delta: timedelta) -> FixedClock:
        return FixedClock(self.instant + delta)
