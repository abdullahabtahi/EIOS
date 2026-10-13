"""Contract every RecordStore must satisfy; the Firestore variant runs only with live credentials."""

import os
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest

from eios.ontology.actions.record_store import (
    FirestoreRecordStore,
    InMemoryRecordStore,
    RecordStore,
    default_record_store,
)

CLOUD = os.getenv("EIOS_TEST_CLOUD") == "1" and bool(os.getenv("GOOGLE_CLOUD_PROJECT"))


@pytest.fixture(
    params=[
        "memory",
        pytest.param(
            "firestore",
            marks=[
                pytest.mark.requires_cloud,
                pytest.mark.skipif(
                    not CLOUD, reason="needs EIOS_TEST_CLOUD=1 and GOOGLE_CLOUD_PROJECT"
                ),
            ],
        ),
    ]
)
def store(request: pytest.FixtureRequest) -> Iterator[RecordStore]:
    if request.param == "memory":
        yield InMemoryRecordStore()
        return
    fs_store = FirestoreRecordStore(collection=f"test_records_{uuid.uuid4().hex[:8]}")
    yield fs_store
    fs_store.delete_all_for_testing()


def test_get_missing_returns_none(store: RecordStore) -> None:
    assert store.get("absent") is None


def test_put_then_get_and_list(store: RecordStore) -> None:
    store.put("a", {"n": 1})
    store.put("b", {"n": 2})
    assert store.get("a") == {"n": 1}
    assert sorted(r["n"] for r in store.list()) == [1, 2]


def test_create_is_exclusive(store: RecordStore) -> None:
    assert store.create("k", {"v": 1}) is True
    assert store.create("k", {"v": 2}) is False
    assert store.get("k") == {"v": 1}


def test_update_applies_mutation_and_returns_result(store: RecordStore) -> None:
    store.put("k", {"n": 1})
    assert store.update("k", lambda r: {**r, "n": r["n"] + 1}) == {"n": 2}
    assert store.get("k") == {"n": 2}


def test_update_missing_raises_key_error(store: RecordStore) -> None:
    with pytest.raises(KeyError):
        store.update("absent", lambda r: r)


def test_update_that_raises_changes_nothing(store: RecordStore) -> None:
    store.put("k", {"n": 1})

    def boom(_: dict) -> dict:
        raise ValueError("rejected")

    with pytest.raises(ValueError, match="rejected"):
        store.update("k", boom)
    assert store.get("k") == {"n": 1}


def test_concurrent_updates_lose_nothing(store: RecordStore) -> None:
    store.put("counter", {"n": 0})
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: store.update("counter", lambda r: {"n": r["n"] + 1}), range(16)))
    assert store.get("counter") == {"n": 16}


def test_concurrent_creates_have_exactly_one_winner(store: RecordStore) -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        wins = list(pool.map(lambda i: store.create("nonce", {"by": i}), range(8)))
    assert wins.count(True) == 1


def test_deployed_environments_refuse_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EIOS_PERSISTENCE", raising=False)
    monkeypatch.setenv("EIOS_ENVIRONMENT", "stage")
    with pytest.raises(RuntimeError, match="EIOS_PERSISTENCE"):
        default_record_store("shelf_tokens")


def test_dev_default_is_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EIOS_PERSISTENCE", raising=False)
    monkeypatch.setenv("EIOS_ENVIRONMENT", "dev")
    assert isinstance(default_record_store("shelf_tokens"), InMemoryRecordStore)
