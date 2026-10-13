"""Durable keyed records for approval state (staged intents, nonces, WORM checkpoints).

``update`` is an atomic read-modify-write and ``create`` an atomic create-if-absent, so two
Cloud Run instances can neither lose an approval nor accept the same nonce twice.
"""

from __future__ import annotations

import os
import random
import threading
import time
from collections.abc import Callable
from typing import Any, Generic, Protocol, TypeVar

from google.api_core.exceptions import Aborted
from pydantic import BaseModel

from eios.ontology.actions.ledger_store import ENVIRONMENT_ENV, LOCAL_ENVIRONMENTS, PERSISTENCE_ENV

Record = dict[str, Any]
Mutation = Callable[[Record], Record]
T = TypeVar("T", bound=BaseModel)

ATTEMPTS = 25
BACKOFF_BASE_SECONDS = 0.02
BACKOFF_CAP_SECONDS = 1.0


class RecordStore(Protocol):
    def get(self, key: str) -> Record | None: ...
    def put(self, key: str, value: Record) -> None: ...
    def create(self, key: str, value: Record) -> bool:
        """Store ``value`` only if ``key`` is absent. Returns whether this call created it."""
        ...

    def update(self, key: str, mutate: Mutation) -> Record:
        """Atomically replace the record with ``mutate(current)``. ``mutate`` must be pure and may raise.

        Raises ``KeyError`` when the record does not exist.
        """
        ...

    def list(self) -> list[Record]: ...


class InMemoryRecordStore:
    """Process-local store for dev and tests. Everything is lost on restart."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, Record] = {}

    def get(self, key: str) -> Record | None:
        with self._lock:
            value = self._data.get(key)
            return dict(value) if value is not None else None

    def put(self, key: str, value: Record) -> None:
        with self._lock:
            self._data[key] = dict(value)

    def create(self, key: str, value: Record) -> bool:
        with self._lock:
            if key in self._data:
                return False
            self._data[key] = dict(value)
            return True

    def update(self, key: str, mutate: Mutation) -> Record:
        with self._lock:
            if key not in self._data:
                raise KeyError(key)
            updated = mutate(dict(self._data[key]))
            self._data[key] = dict(updated)
            return dict(updated)

    def list(self) -> list[Record]:
        with self._lock:
            return [dict(v) for v in self._data.values()]


class FirestoreRecordStore:
    """Firestore-backed store: one document per key in a collection."""

    def __init__(self, collection: str, client: Any = None) -> None:
        from google.cloud import firestore

        self._firestore = firestore
        self._db = client if client is not None else firestore.Client()
        self._col = self._db.collection(collection)

    def get(self, key: str) -> Record | None:
        snapshot = self._col.document(key).get()
        return snapshot.to_dict() if snapshot.exists else None

    def put(self, key: str, value: Record) -> None:
        self._col.document(key).set(value)

    def create(self, key: str, value: Record) -> bool:
        from google.api_core.exceptions import AlreadyExists

        try:
            self._col.document(key).create(value)
            return True
        except AlreadyExists:
            return False

    def update(self, key: str, mutate: Mutation) -> Record:
        ref = self._col.document(key)

        @self._firestore.transactional
        def run(transaction: Any) -> Record:
            snapshot = ref.get(transaction=transaction)
            if not snapshot.exists:
                raise KeyError(key)
            updated: Record = mutate(snapshot.to_dict())
            transaction.set(ref, updated)
            return updated

        last_error: Exception | None = None
        for attempt in range(ATTEMPTS):
            try:
                result: Record = run(self._db.transaction())
                return result
            except (ValueError, Aborted) as exc:
                if isinstance(exc, ValueError) and not isinstance(exc.__cause__, Aborted):
                    raise  # a rejected mutation, not contention
                last_error = exc
                time.sleep(
                    random.uniform(0, min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * 2**attempt))
                )  # noqa: S311
        raise RuntimeError("record contended beyond the retry budget") from last_error

    def list(self) -> list[Record]:
        return [doc.to_dict() for doc in self._col.stream()]

    def delete_all_for_testing(self) -> None:
        for doc in self._col.stream():
            doc.reference.delete()


class ModelStore(Generic[T]):
    """Typed view of a RecordStore for one pydantic model."""

    def __init__(self, store: RecordStore, model: type[T]) -> None:
        self._store = store
        self._model = model

    def _dump(self, value: T) -> Record:
        return value.model_dump(mode="json")

    def get(self, key: str) -> T | None:
        raw = self._store.get(key)
        return self._model.model_validate(raw) if raw is not None else None

    def put(self, key: str, value: T) -> None:
        self._store.put(key, self._dump(value))

    def create(self, key: str, value: T) -> bool:
        return self._store.create(key, self._dump(value))

    def update(self, key: str, mutate: Callable[[T], T]) -> T:
        raw = self._store.update(key, lambda r: self._dump(mutate(self._model.model_validate(r))))
        return self._model.model_validate(raw)

    def list(self) -> list[T]:
        return [self._model.model_validate(r) for r in self._store.list()]


def default_record_store(namespace: str) -> RecordStore:
    """Firestore when EIOS_PERSISTENCE=firestore; in-memory only in dev or test; otherwise fail startup."""
    if os.getenv(PERSISTENCE_ENV) == "firestore":
        return FirestoreRecordStore(collection=f"eios_{namespace}")
    environment = os.getenv(ENVIRONMENT_ENV, "dev")
    if environment not in LOCAL_ENVIRONMENTS:
        raise RuntimeError(
            f"{PERSISTENCE_ENV}=firestore must be set in the '{environment}' environment; "
            "refusing to keep approval state in process memory"
        )
    return InMemoryRecordStore()
