"""T110: counter and replay stores behave identically for memory and firestore."""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest

from eios.common.errors import BoundaryValidationError
from eios.llm_gateway.caps import CounterStore
from eios.llm_gateway.replay_cache import ReplayStore, StoredReplay
from eios.llm_gateway.stores.memory import MemoryCounterStore, MemoryReplayStore

DAY = date(2026, 1, 1)
STORED_AT = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)

BACKENDS = [
    "memory",
    pytest.param("firestore", marks=pytest.mark.requires_emulator),
]


def _stores(backend: str) -> tuple[CounterStore, ReplayStore]:
    if backend == "memory":
        return MemoryCounterStore(), MemoryReplayStore()
    from eios.llm_gateway.stores.firestore import FirestoreCounterStore, FirestoreReplayStore

    namespace = f"test-{uuid.uuid4().hex[:12]}"  # isolates runs against a shared emulator
    return (
        FirestoreCounterStore(project="eios-emulator", collection=f"{namespace}-counters"),
        FirestoreReplayStore(project="eios-emulator", collection=f"{namespace}-replay"),
    )


@pytest.fixture(params=BACKENDS)
def stores(request: pytest.FixtureRequest) -> Iterator[tuple[CounterStore, ReplayStore]]:
    yield _stores(request.param)


def test_add_tokens_returns_the_running_total(stores: tuple[CounterStore, ReplayStore]) -> None:
    counter, _ = stores
    assert counter.add_tokens(DAY, 10) == 10
    assert counter.add_tokens(DAY, 5) == 15
    assert counter.add_tokens(DAY, 0) == 15


def test_days_are_counted_separately(stores: tuple[CounterStore, ReplayStore]) -> None:
    counter, _ = stores
    counter.add_tokens(DAY, 10)
    assert counter.add_tokens(DAY + timedelta(days=1), 3) == 3
    assert counter.add_tokens(DAY, 0) == 10


def test_replay_put_then_get_round_trips(stores: tuple[CounterStore, ReplayStore]) -> None:
    _, replay = stores
    assert replay.get("k1") is None
    replay.put("k1", "cached text", STORED_AT)
    assert replay.get("k1") == StoredReplay(content="cached text", stored_at=STORED_AT)
    assert replay.get("k2") is None


def test_replay_put_overwrites_with_the_latest_value(
    stores: tuple[CounterStore, ReplayStore],
) -> None:
    _, replay = stores
    replay.put("k", "old", STORED_AT)
    later = STORED_AT + timedelta(hours=1)
    replay.put("k", "new", later)
    assert replay.get("k") == StoredReplay(content="new", stored_at=later)


def test_negative_token_counts_are_rejected() -> None:
    with pytest.raises(BoundaryValidationError):
        MemoryCounterStore().add_tokens(DAY, -1)


def test_replay_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(BoundaryValidationError):
        MemoryReplayStore().put("k", "text", datetime(2026, 1, 1))  # noqa: DTZ001


@pytest.mark.parametrize("store_type", ["MemoryCounterStore", "MemoryReplayStore"])
def test_memory_stores_take_no_credentials(store_type: str) -> None:
    cls = {"MemoryCounterStore": MemoryCounterStore, "MemoryReplayStore": MemoryReplayStore}
    assert list(inspect.signature(cls[store_type]).parameters) == []


def test_firestore_stores_take_no_secret_parameters() -> None:
    from eios.llm_gateway.stores.firestore import FirestoreCounterStore, FirestoreReplayStore

    banned = ("secret", "password", "credential", "key", "token")
    for cls in (FirestoreCounterStore, FirestoreReplayStore):
        for name in inspect.signature(cls).parameters:
            assert not any(word in name for word in banned), (cls.__name__, name)
