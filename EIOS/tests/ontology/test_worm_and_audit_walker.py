"""Unit and adversary simulation tests for WORM Checkpoints and Continuous Audit Walker (US4)."""

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.audit import ContinuousAuditWalker
from eios.ontology.actions.models import (
    AuditVerificationReport,
    LedgerEventType,
    WORMAnchorCheckpoint,
)
from eios.ontology.actions.sequencer import LedgerSequencer
from eios.ontology.actions.signer import KMSActionSigner
from eios.ontology.actions.worm import WORMAnchorService, WORMRetentionViolationError
import pytest


def test_worm_anchor_checkpoint_creation_and_immutability():
    engine = HotStateEngine(db_path=":memory:")
    sequencer = LedgerSequencer(hot_state_engine=engine)
    signer = KMSActionSigner(key_id="worm-test-key")
    worm_service = WORMAnchorService(sequencer=sequencer, signer=signer, hot_state_engine=engine)

    # Ingest 5 events
    for i in range(1, 6):
        sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"INTENT-{i}",
            payload={"item": i},
        )

    # Create WORM Checkpoint
    checkpoint = worm_service.create_checkpoint()
    assert isinstance(checkpoint, WORMAnchorCheckpoint)
    assert checkpoint.checkpoint_seq == 1
    assert checkpoint.chain_head_seq == 5
    assert checkpoint.chain_head_hash == sequencer.head_hash
    assert checkpoint.compliance_mode is True
    assert checkpoint.lock_signature is not None

    # Check hot state persistence
    cursor = engine.get_cursor()
    row = cursor.execute(
        "SELECT checkpoint_seq, chain_head_seq, chain_head_hash, compliance_mode FROM worm_anchor_checkpoints WHERE checkpoint_seq = 1"
    ).fetchone()
    assert row is not None
    assert row[0] == 1
    assert row[1] == 5
    assert row[2] == sequencer.head_hash

    # Compliance mode immutability: modification is strictly blocked
    with pytest.raises(WORMRetentionViolationError):
        worm_service.modify_checkpoint_for_testing(checkpoint_seq=1, new_hash="TAMPERED")


def test_continuous_audit_walker_verifies_clean_ledger_with_100_percent_score():
    engine = HotStateEngine(db_path=":memory:")
    sequencer = LedgerSequencer(hot_state_engine=engine)
    worm_service = WORMAnchorService(sequencer=sequencer, hot_state_engine=engine)
    walker = ContinuousAuditWalker(sequencer=sequencer, worm_service=worm_service)

    # Ingest 10 events
    for i in range(1, 11):
        sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"INTENT-{i}",
            payload={"step": i},
        )

    # Create WORM checkpoint at seq 10
    worm_service.create_checkpoint()

    # Run audit walker
    report = walker.verify_ledger()
    assert isinstance(report, AuditVerificationReport)
    assert report.is_valid is True
    assert report.integrity_score == 1.0
    assert report.total_entries == 10
    assert report.tampered_sequence_id is None
    assert report.failure_reason is None
    assert report.worm_checkpoints_verified == 1
    assert report.head_hash == sequencer.head_hash


def test_continuous_audit_walker_detects_single_byte_payload_tampering():
    sequencer = LedgerSequencer()
    worm_service = WORMAnchorService(sequencer=sequencer)
    walker = ContinuousAuditWalker(sequencer=sequencer, worm_service=worm_service)

    # Ingest 5 events
    for i in range(1, 6):
        sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"INTENT-{i}",
            payload={"reason": f"LEGITIMATE_{i}"},
        )

    # Tamper with historical payload at sequence 3
    sequencer.tamper_payload_for_testing(target_seq=3, corrupted_byte_key="reason", corrupted_val="FORGED_PAYLOAD")

    # Run audit walker
    report = walker.verify_ledger()
    assert report.is_valid is False
    assert report.integrity_score < 1.0
    assert report.tampered_sequence_id == 3
    assert "PAYLOAD_DIGEST_MISMATCH" in report.failure_reason or "HASH_MISMATCH" in report.failure_reason


def test_continuous_audit_walker_detects_sequence_gap():
    sequencer = LedgerSequencer()
    worm_service = WORMAnchorService(sequencer=sequencer)
    walker = ContinuousAuditWalker(sequencer=sequencer, worm_service=worm_service)

    # Ingest 4 events
    for i in range(1, 5):
        sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"INTENT-{i}",
            payload={"step": i},
        )

    # Simulate sequence deletion by removing entry 2 from sequencer._entries
    with sequencer._lock:
        del sequencer._entries[1]

    report = walker.verify_ledger()
    assert report.is_valid is False
    assert report.tampered_sequence_id == 3  # Gap detected because expected seq 2 but encountered seq 3
    assert "SEQUENCE_GAP_DETECTED" in report.failure_reason


def test_continuous_audit_walker_detects_worm_anchor_mismatch():
    sequencer = LedgerSequencer()
    worm_service = WORMAnchorService(sequencer=sequencer)
    walker = ContinuousAuditWalker(sequencer=sequencer, worm_service=worm_service)

    for i in range(1, 4):
        sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"INTENT-{i}",
            payload={"step": i},
        )

    cp = worm_service.create_checkpoint()

    # Adversary forges the head hash of entry 3 in the ledger
    with sequencer._lock:
        sequencer._entries[2].current_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    report = walker.verify_ledger()
    assert report.is_valid is False
    assert report.tampered_sequence_id == 3
