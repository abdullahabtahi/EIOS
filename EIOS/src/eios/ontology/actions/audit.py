"""Continuous Cryptographic Audit Walker and Tamper Localization (US4)."""

import time
import uuid
from datetime import UTC, datetime

from eios.ontology.actions.models import AuditVerificationReport
from eios.ontology.actions.sequencer import GENESIS_ANCHOR, LedgerSequencer
from eios.ontology.actions.worm import WORMAnchorService


class ContinuousAuditWalker:
    """Sequentially traverses the ledger to verify mathematical continuity, hash chaining, and WORM anchors."""

    def __init__(
        self,
        sequencer: LedgerSequencer,
        worm_service: WORMAnchorService | None = None,
    ) -> None:
        self.sequencer = sequencer
        self.worm_service = worm_service

    def verify_ledger(self) -> AuditVerificationReport:  # noqa: C901
        """Execute a full sequential audit pass across the cryptographic ledger."""
        start_time = time.perf_counter()
        entries = self.sequencer.entries
        total_entries = len(entries)
        now = datetime.now(UTC)

        report_id = str(uuid.uuid4())
        head_hash = self.sequencer.head_hash

        if total_entries == 0:
            return AuditVerificationReport(
                report_id=report_id,
                verified_at=now,
                total_entries=0,
                genesis_hash=GENESIS_ANCHOR,
                head_hash=GENESIS_ANCHOR,
                is_valid=True,
                integrity_score=1.0,
                tampered_sequence_id=None,
                failure_reason=None,
                worm_checkpoints_verified=0,
                audit_duration_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        expected_seq = 1
        prev_hash = GENESIS_ANCHOR
        valid_links = 0

        for _i, entry in enumerate(entries):
            # 1. Verify sequence monotonicity
            if entry.ledger_seq != expected_seq:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return AuditVerificationReport(
                    report_id=report_id,
                    verified_at=now,
                    total_entries=total_entries,
                    genesis_hash=GENESIS_ANCHOR,
                    head_hash=head_hash,
                    is_valid=False,
                    integrity_score=valid_links / max(total_entries, 1),
                    tampered_sequence_id=entry.ledger_seq,
                    failure_reason=f"SEQUENCE_GAP_DETECTED: Expected sequence {expected_seq} but found {entry.ledger_seq}.",
                    worm_checkpoints_verified=0,
                    audit_duration_ms=duration_ms,
                )

            # 2. Verify predecessor link
            if entry.prev_hash != prev_hash:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return AuditVerificationReport(
                    report_id=report_id,
                    verified_at=now,
                    total_entries=total_entries,
                    genesis_hash=GENESIS_ANCHOR,
                    head_hash=head_hash,
                    is_valid=False,
                    integrity_score=valid_links / max(total_entries, 1),
                    tampered_sequence_id=entry.ledger_seq,
                    failure_reason=f"HASH_MISMATCH: Predecessor hash mismatch at sequence {entry.ledger_seq}.",
                    worm_checkpoints_verified=0,
                    audit_duration_ms=duration_ms,
                )

            # 3. Verify payload digest
            recomputed_payload_digest = self.sequencer.canonical_digest(entry.payload)
            if recomputed_payload_digest != entry.payload_digest:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return AuditVerificationReport(
                    report_id=report_id,
                    verified_at=now,
                    total_entries=total_entries,
                    genesis_hash=GENESIS_ANCHOR,
                    head_hash=head_hash,
                    is_valid=False,
                    integrity_score=valid_links / max(total_entries, 1),
                    tampered_sequence_id=entry.ledger_seq,
                    failure_reason=f"PAYLOAD_DIGEST_MISMATCH: Content tampering detected at sequence {entry.ledger_seq}.",
                    worm_checkpoints_verified=0,
                    audit_duration_ms=duration_ms,
                )

            # 4. Verify current hash digest
            recomputed_hash = self.sequencer.compute_entry_hash(
                prev_hash=entry.prev_hash,
                ledger_seq=entry.ledger_seq,
                payload_digest=entry.payload_digest,
            )
            if recomputed_hash != entry.current_hash:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return AuditVerificationReport(
                    report_id=report_id,
                    verified_at=now,
                    total_entries=total_entries,
                    genesis_hash=GENESIS_ANCHOR,
                    head_hash=head_hash,
                    is_valid=False,
                    integrity_score=valid_links / max(total_entries, 1),
                    tampered_sequence_id=entry.ledger_seq,
                    failure_reason=f"HASH_MISMATCH: Invalid current_hash digest at sequence {entry.ledger_seq}.",
                    worm_checkpoints_verified=0,
                    audit_duration_ms=duration_ms,
                )

            valid_links += 1
            expected_seq += 1
            prev_hash = entry.current_hash

        # 5. Cross-check against WORM compliance checkpoints
        worm_verified = 0
        if self.worm_service:
            for cp in self.worm_service.get_checkpoints():
                if cp.chain_head_seq <= total_entries:
                    matching_entry = entries[cp.chain_head_seq - 1]
                    if matching_entry.current_hash != cp.chain_head_hash:
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        return AuditVerificationReport(
                            report_id=report_id,
                            verified_at=now,
                            total_entries=total_entries,
                            genesis_hash=GENESIS_ANCHOR,
                            head_hash=head_hash,
                            is_valid=False,
                            integrity_score=valid_links / max(total_entries, 1),
                            tampered_sequence_id=cp.chain_head_seq,
                            failure_reason=f"WORM_ANCHOR_MISMATCH: Checkpoint #{cp.checkpoint_seq} hash {cp.chain_head_hash[:16]}... diverges from ledger entry {cp.chain_head_seq}.",
                            worm_checkpoints_verified=worm_verified,
                            audit_duration_ms=duration_ms,
                        )
                    worm_verified += 1

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return AuditVerificationReport(
            report_id=report_id,
            verified_at=now,
            total_entries=total_entries,
            genesis_hash=GENESIS_ANCHOR,
            head_hash=head_hash,
            is_valid=True,
            integrity_score=1.0,
            tampered_sequence_id=None,
            failure_reason=None,
            worm_checkpoints_verified=worm_verified,
            audit_duration_ms=duration_ms,
        )
