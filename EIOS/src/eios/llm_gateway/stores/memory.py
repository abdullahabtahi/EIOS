"""In-memory stores for dev and CI. They hold no credentials and are process-local.

The stores own their state and mutate it under a lock; everything they return is immutable.
"""

from __future__ import annotations

from datetime import date, datetime
from threading import Lock

from eios.common.errors import BoundaryValidationError
from eios.llm_gateway.replay_cache import StoredReplay


def require_non_negative(count: int) -> None:
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise BoundaryValidationError("token count must be a non-negative integer", ("count",))


def require_aware(moment: datetime) -> None:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise BoundaryValidationError("stored_at must be timezone-aware", ("stored_at",))


class MemoryCounterStore:
    def __init__(self) -> None:
        self._totals: dict[date, int] = {}
        self._lock = Lock()

    def add_tokens(self, day: date, count: int) -> int:
        require_non_negative(count)
        with self._lock:
            total = self._totals.get(day, 0) + count
            self._totals[day] = total
            return total


class MemoryReplayStore:
    def __init__(self) -> None:
        self._entries: dict[str, StoredReplay] = {}
        self._lock = Lock()

    def get(self, key: str) -> StoredReplay | None:
        with self._lock:
            return self._entries.get(key)

    def put(self, key: str, content: str, stored_at: datetime) -> None:
        require_aware(stored_at)
        with self._lock:
            self._entries[key] = StoredReplay(content=content, stored_at=stored_at)
