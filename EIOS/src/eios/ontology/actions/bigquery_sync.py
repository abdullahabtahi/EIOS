"""BigQuery External Table and GCS WORM Sync Exporter (ADR-007 / ADR-017, T017)."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from eios.ontology.actions.models import LedgerEntry
from eios.ontology.actions.sequencer import GENESIS_ANCHOR, LedgerSequencer

logger = logging.getLogger("eios.ontology.actions.bigquery_sync")


class BigQueryTamperAlert(Exception):
    """Raised when lakehouse record hash chain diverges from cryptographic ledger head."""

    pass


class BigQueryLedgerExporter:
    """Streams atomically sequenced ledger records to BigQuery and verifies lakehouse continuity."""

    DEFAULT_DATASET = "eios_governance"
    DEFAULT_TABLE = "decision_ledger_worm"

    def __init__(
        self,
        project_id: str = "feios-institutional-prod",
        dataset_id: str = DEFAULT_DATASET,
        table_id: str = DEFAULT_TABLE,
        dry_run: bool = True,
    ) -> None:
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.dry_run = dry_run
        self._buffered_rows: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def format_row(self, entry: LedgerEntry) -> Dict[str, Any]:
        """Formats ledger entry into BigQuery external table schema."""
        current_hash = getattr(entry, "current_hash", getattr(entry, "entry_hash", ""))
        return {
            "ledger_seq": entry.ledger_seq,
            "prev_hash": entry.prev_hash,
            "entry_hash": current_hash,
            "current_hash": current_hash,
            "event_type": entry.event_type.value
            if hasattr(entry.event_type, "value")
            else str(entry.event_type),
            "entity_id": entry.entity_id,
            "payload_digest": entry.payload_digest,
            "payload_json": json.dumps(entry.payload, sort_keys=True),
            "recorded_at": entry.recorded_at.isoformat()
            if hasattr(entry.recorded_at, "isoformat")
            else str(entry.recorded_at),
            "kms_key_version": getattr(
                entry, "kms_key_version", "projects/feios/cryptoKeys/ledger-v1"
            ),
            "ingested_to_bq_at": datetime.now(UTC).isoformat(),
        }

    def stream_entry(self, entry: LedgerEntry) -> Dict[str, Any]:
        """Streams a finalized ledger entry with atomic sequence to BigQuery buffer."""
        row = self.format_row(entry)
        with self._lock:
            self._buffered_rows.append(row)
        logger.info(
            "Streamed ledger seq=%d (entry_hash=%.12s...) to BigQuery table %s.%s",
            entry.ledger_seq,
            row["entry_hash"],
            self.dataset_id,
            self.table_id,
        )
        return row

    def get_buffered_rows(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._buffered_rows)

    def verify_lakehouse_integrity(
        self,
        lakehouse_records: Optional[List[Dict[str, Any]]] = None,
        expected_head_hash: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Cryptographically verifies monotonic SHA-256 hash chaining of BigQuery records.

        Evaluates H_i = SHA-256(prev_hash || ledger_seq || payload_digest).
        Detects tampering, out-of-order sequence injections, and altered payloads.
        """
        records = lakehouse_records if lakehouse_records is not None else self.get_buffered_rows()
        if not records:
            return True, []

        findings: List[str] = []
        expected_prev = GENESIS_ANCHOR
        expected_seq = 1

        for idx, row in enumerate(records):
            seq = row.get("ledger_seq")
            prev_hash = row.get("prev_hash")
            entry_hash = row.get("entry_hash")
            payload_digest = row.get("payload_digest")

            # 1. Monotonic Sequence Continuity Check
            if seq != expected_seq:
                findings.append(
                    f"Sequence break at row {idx}: expected ledger_seq {expected_seq}, found {seq}"
                )

            # 2. Previous Hash Parent Chaining Check
            if prev_hash != expected_prev:
                findings.append(
                    f"Hash pointer break at seq {seq}: prev_hash '{prev_hash}' does not match expected '{expected_prev}'"
                )

            # 3. Cryptographic Recalculation Check
            computed_hash = hashlib.sha256(
                f"{prev_hash}{seq}{payload_digest}".encode("utf-8")
            ).hexdigest()
            if computed_hash != entry_hash:
                findings.append(
                    f"Cryptographic divergence at seq {seq}: computed hash '{computed_hash}' != stored entry_hash '{entry_hash}' (tampered record!)"
                )

            expected_prev = entry_hash
            expected_seq += 1

        # 4. Check against external GCS WORM head checkpoint
        if expected_head_hash and records:
            last_entry_hash = records[-1].get("entry_hash")
            if last_entry_hash != expected_head_hash:
                findings.append(
                    f"Chain-head divergence: BigQuery lakehouse head '{last_entry_hash}' does not match GCS WORM anchor '{expected_head_hash}'"
                )

        is_valid = len(findings) == 0
        return is_valid, findings
