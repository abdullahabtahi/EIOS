"""Upstream Atomic Monotonic Sequencer and Cryptographic Hash Chain Ledger (ADR-017 / US1)."""

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.ledger_store import (
    GENESIS_ANCHOR,
    InMemoryLedgerStore,
    LedgerStore,
    default_ledger_store,
)
from eios.ontology.actions.models import LedgerEntry, LedgerEventType

__all__ = ["GENESIS_ANCHOR", "LedgerSequencer", "SequenceIntegrityError"]


class SequenceIntegrityError(Exception):
    """Raised when sequence monotonicity or cryptographic hash chaining is violated."""

    pass


class LedgerSequencer:
    """Coordinates upstream total ordering and SHA-256 hash chaining prior to analytical persistence."""

    def __init__(
        self, hot_state_engine: HotStateEngine | None = None, store: LedgerStore | None = None
    ) -> None:
        self._hot_state = hot_state_engine
        self._store: LedgerStore = store if store is not None else default_ledger_store()

    @property
    def current_seq(self) -> int:
        return self._store.head()[0]

    @property
    def head_hash(self) -> str:
        return self._store.head()[1]

    @property
    def entries(self) -> list[LedgerEntry]:
        return self._store.list_entries()

    # Disaster-recovery and tamper-drill hooks. They operate on the in-memory store only.
    def _memory_store(self) -> InMemoryLedgerStore:
        if not isinstance(self._store, InMemoryLedgerStore):
            raise SequenceIntegrityError(
                "direct ledger manipulation is only available on the in-memory store"
            )
        return self._store

    @property
    def _lock(self) -> Any:
        return self._memory_store()._lock

    @property
    def _entries(self) -> list[LedgerEntry]:
        return self._memory_store().entries

    @property
    def _current_seq(self) -> int:
        return self._memory_store().seq

    @_current_seq.setter
    def _current_seq(self, value: int) -> None:
        self._memory_store().seq = value

    @property
    def _head_hash(self) -> str:
        return self._memory_store().hash

    @_head_hash.setter
    def _head_hash(self, value: str) -> None:
        self._memory_store().hash = value

    def canonical_digest(self, payload: dict[str, Any]) -> str:
        """Produce deterministic SHA-256 hex digest of RFC 8785 canonical JSON payload."""
        canonical_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def compute_entry_hash(self, prev_hash: str, ledger_seq: int, payload_digest: str) -> str:
        """Compute cryptographic hash link H_i = SHA-256(prev_hash || ledger_seq || payload_digest)."""
        chain_bytes = f"{prev_hash}{ledger_seq}{payload_digest}".encode("utf-8")
        return hashlib.sha256(chain_bytes).hexdigest()

    def record_event(
        self,
        event_type: LedgerEventType,
        entity_id: str,
        payload: dict[str, Any],
        worm_checkpoint_seq: int | None = None,
    ) -> LedgerEntry:
        """Atomically assign strictly monotonic sequence number and cryptographically chain event."""

        def build(head_seq: int, head_hash: str) -> LedgerEntry:
            next_seq = head_seq + 1
            payload_digest = self.canonical_digest(payload)
            return LedgerEntry(
                ledger_seq=next_seq,
                prev_hash=head_hash,
                current_hash=self.compute_entry_hash(
                    prev_hash=head_hash, ledger_seq=next_seq, payload_digest=payload_digest
                ),
                event_type=event_type,
                entity_id=entity_id,
                payload_digest=payload_digest,
                payload=payload,
                recorded_at=datetime.now(UTC),
                worm_checkpoint_seq=worm_checkpoint_seq,
            )

        entry = self._store.append(build)
        if self._hot_state:
            self._persist_to_hot_state(entry)
        return entry

    def _persist_to_hot_state(self, entry: LedgerEntry) -> None:
        """Persist serialized entry into DuckDB atomic_sequence_ledger table."""
        cursor = self._hot_state.get_cursor()
        cursor.execute(
            """
            INSERT INTO atomic_sequence_ledger (
                ledger_seq, prev_hash, current_hash, event_type, entity_id,
                payload_digest, payload, recorded_at, worm_checkpoint_seq
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                entry.ledger_seq,
                entry.prev_hash,
                entry.current_hash,
                entry.event_type.value
                if hasattr(entry.event_type, "value")
                else str(entry.event_type),
                entry.entity_id,
                entry.payload_digest,
                json.dumps(entry.payload),
                entry.recorded_at,
                entry.worm_checkpoint_seq,
            ],
        )

    def get_entry(self, seq: int) -> LedgerEntry | None:
        """Retrieve entry by sequence number."""
        return self._store.get(seq)

    def get_entries_by_event(self, event_type: str | LedgerEventType) -> list[LedgerEntry]:
        """Retrieve entries matching specified event type."""
        ev_str = event_type.value if hasattr(event_type, "value") else str(event_type)
        return [
            e
            for e in self._store.list_entries()
            if (e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type))
            == ev_str
        ]

    def tamper_payload_for_testing(
        self, target_seq: int, corrupted_byte_key: str, corrupted_val: Any
    ) -> None:
        """Simulate adversarial payload corruption for continuous audit walker testing (in-memory only)."""
        entries = self._memory_store().entries
        if 1 <= target_seq <= len(entries):
            # Intentionally do not recompute current_hash, simulating stealth database tamper
            entries[target_seq - 1].payload[corrupted_byte_key] = corrupted_val
