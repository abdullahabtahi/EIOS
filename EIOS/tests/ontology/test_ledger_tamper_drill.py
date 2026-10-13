"""Tamper-Evidence Verification Drill for BigQuery External Table Records (ADR-007 / ADR-017, T018)."""

from eios.ontology.actions.bigquery_sync import BigQueryLedgerExporter
from eios.ontology.actions.models import LedgerEventType
from eios.ontology.actions.sequencer import LedgerSequencer


def test_pristine_ledger_sync_and_lakehouse_verification():
    sequencer = LedgerSequencer()
    exporter = BigQueryLedgerExporter()

    # Record 5 real events through the monotonic sequencer
    for i in range(1, 6):
        entry = sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"ENTITY-{i:03d}",
            payload={"action": "HoldWithdrawal", "index": i, "amount": 1000.0 * i},
        )
        exporter.stream_entry(entry)

    buffered = exporter.get_buffered_rows()
    assert len(buffered) == 5
    assert buffered[0]["ledger_seq"] == 1
    assert buffered[-1]["ledger_seq"] == 5

    # Verification must pass 100% cleanly against the sequencer's head hash
    is_valid, findings = exporter.verify_lakehouse_integrity(expected_head_hash=sequencer.head_hash)
    assert is_valid is True
    assert findings == []


def test_tamper_drill_detects_modified_payload():
    sequencer = LedgerSequencer()
    exporter = BigQueryLedgerExporter()

    for i in range(1, 4):
        entry = sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"ENTITY-{i:03d}",
            payload={"action": "HoldWithdrawal", "amount": 500.0 * i},
        )
        exporter.stream_entry(entry)

    tampered_records = exporter.get_buffered_rows()

    # Malicious injection / alteration in BigQuery record #2: change payload_digest
    tampered_records[1]["payload_digest"] = (
        "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    )

    is_valid, findings = exporter.verify_lakehouse_integrity(tampered_records)
    assert is_valid is False
    assert len(findings) >= 1
    assert any("Cryptographic divergence at seq 2" in f for f in findings)


def test_tamper_drill_detects_sequence_deletion():
    sequencer = LedgerSequencer()
    exporter = BigQueryLedgerExporter()

    for i in range(1, 5):
        entry = sequencer.record_event(
            event_type=LedgerEventType.ACTION_EXECUTED,
            entity_id=f"ACC-{i:03d}",
            payload={"side_effects": {"status": "COMMITTED"}},
        )
        exporter.stream_entry(entry)

    tampered_records = exporter.get_buffered_rows()
    # Delete row seq=2
    del tampered_records[1]

    is_valid, findings = exporter.verify_lakehouse_integrity(tampered_records)
    assert is_valid is False
    assert any("Sequence break at row 1" in f for f in findings)


def test_tamper_drill_detects_divergence_from_worm_anchor():
    sequencer = LedgerSequencer()
    exporter = BigQueryLedgerExporter()

    entry = sequencer.record_event(
        event_type=LedgerEventType.PROPOSAL_CREATED,
        entity_id="ACC-001",
        payload={"action": "Test"},
    )
    exporter.stream_entry(entry)

    # Valid chain but head doesn't match official GCS WORM anchor
    fake_worm_anchor = "1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff"
    is_valid, findings = exporter.verify_lakehouse_integrity(expected_head_hash=fake_worm_anchor)
    assert is_valid is False
    assert any("Chain-head divergence" in f for f in findings)
