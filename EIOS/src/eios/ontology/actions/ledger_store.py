"""Durable storage for the hash-chained decision ledger (ADR-017).

``append`` is the only write path. It builds the next entry from the current head and persists
the entry and the new head in one atomic step, so concurrent writers on separate instances can
neither fork the chain nor leave a gap.
"""

from __future__ import annotations

import hashlib
import os
import random
import threading
import time
from collections.abc import Callable
from typing import Any, Protocol

from google.api_core.exceptions import Aborted

from eios.ontology.actions.models import LedgerEntry

# Pre-registered Genesis Anchor (SHA-256 of "EIOS_GENESIS_ANCHOR_V1_20261008")
GENESIS_ANCHOR: str = hashlib.sha256(b"EIOS_GENESIS_ANCHOR_V1_20261008").hexdigest()

PERSISTENCE_ENV = "EIOS_PERSISTENCE"
ENVIRONMENT_ENV = "EIOS_ENVIRONMENT"
LOCAL_ENVIRONMENTS = frozenset({"dev", "test"})

EntryBuilder = Callable[[int, str], LedgerEntry]

APPEND_ATTEMPTS = 25
BACKOFF_BASE_SECONDS = 0.02
BACKOFF_CAP_SECONDS = 1.0


class LedgerContentionError(RuntimeError):
    """The ledger head stayed contended past the retry budget; the caller may retry the operation."""


class LedgerStore(Protocol):
    def head(self) -> tuple[int, str]:
        """Return (last sequence number, last chain hash); (0, genesis) when empty."""
        ...

    def append(self, build: EntryBuilder) -> LedgerEntry:
        """Atomically build the next entry from the head and persist it with the new head.

        ``build`` must be pure: a transactional store may call it more than once on contention.
        """
        ...

    def get(self, seq: int) -> LedgerEntry | None: ...

    def list_entries(self) -> list[LedgerEntry]: ...


class InMemoryLedgerStore:
    """Process-local store for dev and tests. Everything is lost on restart."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.entries: list[LedgerEntry] = []
        self.seq: int = 0
        self.hash: str = GENESIS_ANCHOR

    def head(self) -> tuple[int, str]:
        with self._lock:
            return self.seq, self.hash

    def append(self, build: EntryBuilder) -> LedgerEntry:
        with self._lock:
            entry = build(self.seq, self.hash)
            self.entries.append(entry)
            self.seq, self.hash = entry.ledger_seq, entry.current_hash
            return entry

    def get(self, seq: int) -> LedgerEntry | None:
        with self._lock:
            return self.entries[seq - 1] if 1 <= seq <= len(self.entries) else None

    def list_entries(self) -> list[LedgerEntry]:
        with self._lock:
            return list(self.entries)


class FirestoreLedgerStore:
    """Firestore-backed store. One document per entry plus a head document, written in a transaction."""

    def __init__(self, client: Any = None, collection_prefix: str = "eios_ledger") -> None:
        from google.cloud import firestore

        self._firestore = firestore
        self._db = client if client is not None else firestore.Client()
        self._entries = self._db.collection(f"{collection_prefix}_entries")
        self._head_ref = self._db.collection(f"{collection_prefix}_meta").document("head")

    @staticmethod
    def _doc_id(seq: int) -> str:
        return f"{seq:012d}"

    def head(self) -> tuple[int, str]:
        snapshot = self._head_ref.get()
        if not snapshot.exists:
            return 0, GENESIS_ANCHOR
        return int(snapshot.get("seq")), str(snapshot.get("hash"))

    def append(self, build: EntryBuilder) -> LedgerEntry:
        @self._firestore.transactional
        def run(transaction: Any) -> LedgerEntry:
            snapshot = self._head_ref.get(transaction=transaction)
            seq, chain_hash = (
                (int(snapshot.get("seq")), str(snapshot.get("hash")))
                if snapshot.exists
                else (0, GENESIS_ANCHOR)
            )
            entry = build(seq, chain_hash)
            transaction.set(
                self._entries.document(self._doc_id(entry.ledger_seq)),
                entry.model_dump(mode="json"),
            )
            transaction.set(self._head_ref, {"seq": entry.ledger_seq, "hash": entry.current_hash})
            return entry

        # Every append serialises on the head document, so contention is expected under parallel
        # writers. Approvals are low-volume; this keeps the chain strictly gap-free at that rate.
        last_error: Exception | None = None
        for attempt in range(APPEND_ATTEMPTS):
            try:
                appended: LedgerEntry = run(self._db.transaction())
                return appended
            except (ValueError, Aborted) as exc:  # SDK attempts exhausted, or aborted by contention
                last_error = exc
                delay = min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * 2**attempt)
                time.sleep(random.uniform(0, delay))  # noqa: S311 - jitter, not cryptography
        raise LedgerContentionError("ledger head contended beyond the retry budget") from last_error

    def get(self, seq: int) -> LedgerEntry | None:
        snapshot = self._entries.document(self._doc_id(seq)).get()
        return LedgerEntry.model_validate(snapshot.to_dict()) if snapshot.exists else None

    def list_entries(self) -> list[LedgerEntry]:
        return [
            LedgerEntry.model_validate(doc.to_dict())
            for doc in self._entries.order_by("ledger_seq").stream()
        ]

    def delete_all_for_testing(self) -> None:
        for doc in self._entries.stream():
            doc.reference.delete()
        self._head_ref.delete()


def default_ledger_store() -> LedgerStore:
    """Firestore when EIOS_PERSISTENCE=firestore; in-memory only in dev or test; otherwise fail startup."""
    if os.getenv(PERSISTENCE_ENV) == "firestore":
        return FirestoreLedgerStore()
    environment = os.getenv(ENVIRONMENT_ENV, "dev")
    if environment not in LOCAL_ENVIRONMENTS:
        raise RuntimeError(
            f"{PERSISTENCE_ENV}=firestore must be set in the '{environment}' environment; "
            "refusing to keep the decision ledger in process memory"
        )
    return InMemoryLedgerStore()
