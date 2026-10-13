"""Immutable WORM Chain-Head Anchoring Service (GCS Compliance Mode / US4)."""

from datetime import UTC, datetime, timedelta
import threading
from typing import Any

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.models import WORMAnchorCheckpoint
from eios.ontology.actions.sequencer import LedgerSequencer
from eios.ontology.actions.record_store import ModelStore, RecordStore, default_record_store
from eios.ontology.actions.signer import ActionSigner, default_action_signer


class WORMRetentionViolationError(Exception):
    """Raised when an attempt is made to overwrite, alter, or delete a WORM compliance-locked record."""

    pass


class WORMAnchorService:
    """Simulates Google Cloud Storage Object Retention Lock in Compliance Mode."""

    RETENTION_YEARS: int = 7

    def __init__(
        self,
        sequencer: LedgerSequencer,
        signer: ActionSigner | None = None,
        hot_state_engine: HotStateEngine | None = None,
        checkpoint_records: RecordStore | None = None,
    ) -> None:
        self.sequencer = sequencer
        self.signer = signer or default_action_signer()
        self.hot_state = hot_state_engine
        self._checkpoints = ModelStore(
            checkpoint_records or default_record_store("worm_checkpoints"), WORMAnchorCheckpoint
        )
        self._lock = threading.Lock()

    def create_checkpoint(self) -> WORMAnchorCheckpoint:
        """Lock the latest chain-head sequence and hash into immutable compliance storage.

        The checkpoint sequence is claimed with an atomic create-if-absent, so two instances can
        never issue the same checkpoint number.
        """
        while True:
            head_seq = self.sequencer.current_seq
            head_hash = self.sequencer.head_hash
            next_cp_seq = len(self._checkpoints.list()) + 1
            now = datetime.now(UTC)
            retention_until = now + timedelta(days=365 * self.RETENTION_YEARS)

            signing_payload = {
                "checkpoint_seq": next_cp_seq,
                "chain_head_seq": head_seq,
                "chain_head_hash": head_hash,
                "locked_at": now.isoformat(),
                "retention_until": retention_until.isoformat(),
                "compliance_mode": True,
            }
            checkpoint = WORMAnchorCheckpoint(
                checkpoint_seq=next_cp_seq,
                chain_head_seq=head_seq,
                chain_head_hash=head_hash,
                locked_at=now,
                retention_until=retention_until,
                compliance_mode=True,
                lock_signature=self.signer.sign_payload(signing_payload),
            )
            if self._checkpoints.create(f"{next_cp_seq:012d}", checkpoint):
                break

        if self.hot_state:
            self._persist_to_hot_state(checkpoint)
        return checkpoint

    def get_checkpoints(self) -> list[WORMAnchorCheckpoint]:
        return sorted(self._checkpoints.list(), key=lambda c: c.checkpoint_seq)

    def get_checkpoint(self, seq: int) -> WORMAnchorCheckpoint | None:
        with self._lock:
            if 1 <= seq <= len(self._checkpoints):
                return self._checkpoints[seq - 1]
            return None

    def _persist_to_hot_state(self, cp: WORMAnchorCheckpoint) -> None:
        """Persist compliance lock record into DuckDB worm_anchor_checkpoints table."""
        cursor = self.hot_state.get_cursor()
        cursor.execute(
            """
            INSERT INTO worm_anchor_checkpoints (
                checkpoint_seq, chain_head_seq, chain_head_hash,
                locked_at, retention_until, compliance_mode, lock_signature
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                cp.checkpoint_seq,
                cp.chain_head_seq,
                cp.chain_head_hash,
                cp.locked_at,
                cp.retention_until,
                cp.compliance_mode,
                cp.lock_signature,
            ],
        )

    def modify_checkpoint_for_testing(self, checkpoint_seq: int, new_hash: str) -> None:
        """Enforces immutability: compliance lock rejects any mutation attempts."""
        raise WORMRetentionViolationError(
            f"WORM Compliance Lock in active mode prohibits mutation or deletion of checkpoint #{checkpoint_seq}."
        )
