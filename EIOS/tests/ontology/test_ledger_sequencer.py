"""Unit and property tests for Upstream Monotonic Sequencer and Cryptographic Hash Chaining (US1)."""

import concurrent.futures
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.models import LedgerEntry, LedgerEventType
from eios.ontology.actions.sequencer import (
    GENESIS_ANCHOR,
    LedgerSequencer,
    SequenceIntegrityError,
)
import pytest


def test_sequencer_initializes_with_genesis_anchor():
    sequencer = LedgerSequencer()
    assert sequencer.current_seq == 0
    assert sequencer.head_hash == GENESIS_ANCHOR
    assert len(sequencer.entries) == 0


def test_sequencer_assigns_strictly_monotonic_sequence_numbers():
    sequencer = LedgerSequencer()

    entry1 = sequencer.record_event(
        event_type=LedgerEventType.PROPOSAL_CREATED,
        entity_id="INTENT-001",
        payload={"action_type": "HoldWithdrawal", "status": "PENDING"},
    )
    assert entry1.ledger_seq == 1
    assert entry1.prev_hash == GENESIS_ANCHOR
    assert len(entry1.current_hash) == 64

    entry2 = sequencer.record_event(
        event_type=LedgerEventType.APPROVAL_RECORDED,
        entity_id="INTENT-001",
        payload={"approver_id": "OFFICER_A", "role": "MLRO"},
    )
    assert entry2.ledger_seq == 2
    assert entry2.prev_hash == entry1.current_hash

    entry3 = sequencer.record_event(
        event_type=LedgerEventType.ACTION_EXECUTED,
        entity_id="INTENT-001",
        payload={"receipt_id": "REC-001", "status": "COMMITTED"},
    )
    assert entry3.ledger_seq == 3
    assert entry3.prev_hash == entry2.current_hash

    assert sequencer.current_seq == 3
    assert sequencer.head_hash == entry3.current_hash


def test_sequencer_persists_to_hot_state():
    engine = HotStateEngine(db_path=":memory:")
    sequencer = LedgerSequencer(hot_state_engine=engine)

    entry = sequencer.record_event(
        event_type=LedgerEventType.PROPOSAL_CREATED,
        entity_id="INTENT-100",
        payload={"action_type": "FreezeAccount", "client_id": "C-101"},
    )

    cursor = engine.get_cursor()
    row = cursor.execute(
        "SELECT ledger_seq, prev_hash, current_hash, event_type, entity_id FROM atomic_sequence_ledger WHERE ledger_seq = 1"
    ).fetchone()

    assert row is not None
    assert row[0] == 1
    assert row[1] == GENESIS_ANCHOR
    assert row[2] == entry.current_hash
    assert row[3] == "PROPOSAL_CREATED"
    assert row[4] == "INTENT-100"


def test_sequencer_computes_deterministic_sha256_chain():
    sequencer = LedgerSequencer()
    payload = {"symbol": "BTCUSD", "amount": 1000.0}

    entry = sequencer.record_event(
        event_type=LedgerEventType.PROPOSAL_CREATED,
        entity_id="INTENT-500",
        payload=payload,
    )

    # Recompute independently
    expected_payload_digest = sequencer.canonical_digest(payload)
    expected_hash = sequencer.compute_entry_hash(
        prev_hash=GENESIS_ANCHOR,
        ledger_seq=1,
        payload_digest=expected_payload_digest,
    )

    assert entry.payload_digest == expected_payload_digest
    assert entry.current_hash == expected_hash


def test_sequencer_concurrent_writes_are_strictly_serialized():
    sequencer = LedgerSequencer()
    n_threads = 20

    def write_event(idx: int):
        return sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"CONCURRENT-{idx}",
            payload={"index": idx},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(write_event, range(n_threads)))

    assert len(results) == n_threads
    seq_nums = [r.ledger_seq for r in sequencer.entries]
    assert seq_nums == list(range(1, n_threads + 1))

    # Verify unbroken hash chain
    for i in range(1, len(sequencer.entries)):
        prev_entry = sequencer.entries[i - 1]
        curr_entry = sequencer.entries[i]
        assert curr_entry.prev_hash == prev_entry.current_hash
