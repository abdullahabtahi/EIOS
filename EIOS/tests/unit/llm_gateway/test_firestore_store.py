"""Firestore store logic against an in-memory fake, so it is covered without the emulator."""

from __future__ import annotations

import os
import subprocess
import sys
import types
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from eios.common.errors import BoundaryValidationError, ToolError
from eios.llm_gateway.replay_cache import StoredReplay
from eios.llm_gateway.stores.firestore import FirestoreCounterStore, FirestoreReplayStore

SRC = Path(__file__).resolve().parents[3] / "src"
DAY = date(2026, 1, 1)
NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


class FakeSnapshot:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return None if self._data is None else dict(self._data)


class FakeDocument:
    def __init__(self, store: dict[str, dict[str, Any]], doc_id: str) -> None:
        self._store, self.doc_id = store, doc_id

    def get(self, transaction: object = None) -> FakeSnapshot:
        return FakeSnapshot(self._store.get(self.doc_id))

    def set(self, data: dict[str, Any]) -> None:
        self._store[self.doc_id] = dict(data)


class FakeTransaction:
    def set(self, ref: FakeDocument, data: dict[str, Any]) -> None:
        ref.set(data)


class FakeCollection:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self._store = store

    def document(self, doc_id: str) -> FakeDocument:
        return FakeDocument(self._store, doc_id)


class FakeClient:
    def __init__(self, project: str | None = None) -> None:
        self.project = project
        self.collections: dict[str, dict[str, dict[str, Any]]] = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self.collections.setdefault(name, {}))

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()


def _transactional(fn: Callable[..., Any]) -> Callable[..., Any]:
    return lambda transaction, *args: fn(transaction, *args)


@pytest.fixture
def fake_firestore(monkeypatch: pytest.MonkeyPatch) -> Iterator[types.ModuleType]:
    module = types.ModuleType("google.cloud.firestore")
    module.Client = FakeClient  # type: ignore[attr-defined]
    module.transactional = _transactional  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", module)
    yield module


def test_counter_accumulates_per_day_and_reuses_the_client(
    fake_firestore: types.ModuleType,
) -> None:
    store = FirestoreCounterStore(project="p", collection="c")
    assert store.add_tokens(DAY, 10) == 10
    assert store.add_tokens(DAY, 5) == 15
    assert store.add_tokens(date(2026, 1, 2), 3) == 3
    assert store.add_tokens(DAY, 0) == 15


def test_counter_writes_to_the_supplied_client_and_collection(
    fake_firestore: types.ModuleType,
) -> None:
    client = FakeClient("p")
    FirestoreCounterStore(project="p", collection="c", client=client).add_tokens(DAY, 7)
    assert client.collections["c"][DAY.isoformat()] == {"tokens": 7}


def test_counter_rejects_negative_counts(fake_firestore: types.ModuleType) -> None:
    with pytest.raises(BoundaryValidationError):
        FirestoreCounterStore(project="p").add_tokens(DAY, -1)


def test_counter_rejects_a_corrupt_stored_total(fake_firestore: types.ModuleType) -> None:
    client = FakeClient("p")
    client.collection("c").document(DAY.isoformat()).set({"tokens": "lots"})
    store = FirestoreCounterStore(project="p", collection="c", client=client)
    with pytest.raises(BoundaryValidationError):
        store.add_tokens(DAY, 1)


def test_replay_round_trips_and_overwrites(fake_firestore: types.ModuleType) -> None:
    store = FirestoreReplayStore(project="p", collection="r")
    assert store.get("k") is None
    store.put("k", "text", NOW)
    assert store.get("k") == StoredReplay(content="text", stored_at=NOW)
    store.put("k", "newer", NOW)
    assert store.get("k") == StoredReplay(content="newer", stored_at=NOW)


def test_replay_rejects_naive_timestamps(fake_firestore: types.ModuleType) -> None:
    with pytest.raises(BoundaryValidationError):
        FirestoreReplayStore(project="p").put("k", "t", datetime(2026, 1, 1))  # noqa: DTZ001


def test_replay_treats_a_malformed_document_as_a_miss_and_logs(
    fake_firestore: types.ModuleType, caplog: pytest.LogCaptureFixture
) -> None:
    client = FakeClient("p")
    client.collection("r").document("k").set({"content": 5, "stored_at": "yesterday"})
    store = FirestoreReplayStore(project="p", collection="r", client=client)
    with caplog.at_level("WARNING"):
        assert store.get("k") is None
    assert "malformed" in caplog.text


def test_missing_dependency_is_a_typed_error_with_install_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", None)
    with pytest.raises(ToolError) as caught:
        FirestoreCounterStore(project="p").add_tokens(DAY, 1)
    assert "google-cloud-firestore" in str(caught.value)


def test_importing_the_module_does_not_import_the_sdk() -> None:
    code = (
        "import sys, eios.llm_gateway.stores.firestore;"
        "sys.exit(1 if 'google.cloud.firestore' in sys.modules else 0)"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    result = subprocess.run([sys.executable, "-c", code], env=env, check=False)  # noqa: S603
    assert result.returncode == 0
