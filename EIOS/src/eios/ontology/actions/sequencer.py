"""Upstream Atomic Monotonic Sequencer and Cryptographic Hash Chain Ledger (ADR-017 / US1)."""

from datetime import UTC, datetime
import hashlib
import json
import threading
from typing import Any

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.models import LedgerEntry, LedgerEventType

# Pre-registered Genesis Anchor (SHA-256 of "EIOS_GENESIS_ANCHOR_V1_20261008")
GENESIS_ANCHOR: str = hashlib.sha256(b"EIOS_GENESIS_ANCHOR_V1_20261008").hexdigest()


class SequenceIntegrityError(Exception):
    """Raised when sequence monotonicity or cryptographic hash chaining is violated."""

    pass


class LedgerSequencer:
    """Coordinates upstream total ordering and SHA-256 hash chaining prior to analytical persistence."""

    def __init__(self, hot_state_engine: HotStateEngine | None = None) -> None:
        self._lock = threading.Lock()
        self._hot_state = hot_state_engine
        self._entries: list[LedgerEntry] = []
        self._current_seq: int = 0
        self._head_hash: str = GENESIS_ANCHOR

    @property
    def current_seq(self) -> int:
        with self._lock:
            return self._current_seq

    @property
    def head_hash(self) -> str:
        with self._lock:
            return self._head_hash

    @property
    def entries(self) -> list[LedgerEntry]:
        with self._lock:
            return list(self._entries)

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
        with self._lock:
            next_seq = self._current_seq + 1
            prev_hash = self._head_hash
            payload_digest = self.canonical_digest(payload)
            current_hash = self.compute_entry_hash(
                prev_hash=prev_hash,
                ledger_seq=next_seq,
                payload_digest=payload_digest,
            )

            now = datetime.now(UTC)
            entry = LedgerEntry(
                ledger_seq=next_seq,
                prev_hash=prev_hash,
                current_hash=current_hash,
                event_type=event_type,
                entity_id=entity_id,
                payload_digest=payload_digest,
                payload=payload,
                recorded_at=now,
                worm_checkpoint_seq=worm_checkpoint_seq,
            )

            self._entries.append(entry)
            self._current_seq = next_seq
            self._head_hash = current_hash

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
                entry.event_type.value if hasattr(entry.event_type, "value") else str(entry.event_type),
                entry.entity_id,
                entry.payload_digest,
                json.dumps(entry.payload),
                entry.recorded_at,
                entry.worm_checkpoint_seq,
            ],
        )

    def get_entry(self, seq: int) -> LedgerEntry | None:
        """Retrieve entry by sequence number."""
        with self._lock:
            if 1 <= seq <= len(self._entries):
                return self._entries[seq - 1]
            return None

    def get_entries_by_event(self, event_type: str | LedgerEventType) -> list[LedgerEntry]:
        """Retrieve entries matching specified event type."""
        ev_str = event_type.value if hasattr(event_type, "value") else str(event_type)
        with self._lock:
            return [
                e for e in self._entries
                if (e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type)) == ev_str
            ]

    def tamper_payload_for_testing(self, target_seq: int, corrupted_byte_key: str, corrupted_val: Any) -> None:
        """Simulate adversarial payload corruption for continuous audit walker testing."""
        with self._lock:
            if 1 <= target_seq <= len(self._entries):
                entry = self._entries[target_seq - 1]
                entry.payload[corrupted_byte_key] = corrupted_val
                # Intentionally do not recompute current_hash, simulating stealth database tamper
