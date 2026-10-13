"""Contract every LedgerStore must satisfy; the Firestore variant runs only with live credentials."""

import os
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest

from eios.ontology.actions.ledger_store import (
    GENESIS_ANCHOR,
    FirestoreLedgerStore,
    InMemoryLedgerStore,
    LedgerStore,
)
from eios.ontology.actions.models import LedgerEventType
from eios.ontology.actions.sequencer import LedgerSequencer

CLOUD = os.getenv("EIOS_TEST_CLOUD") == "1" and bool(os.getenv("GOOGLE_CLOUD_PROJECT"))


@pytest.fixture(
    params=[
        "memory",
        pytest.param(
            "firestore",
            marks=[
                pytest.mark.requires_cloud,
                pytest.mark.skipif(
                    not CLOUD, reason="needs EIOS_TEST_CLOUD=1 and GOOGLE_CLOUD_PROJECT"
                ),
            ],
        ),
    ]
)
def store(request: pytest.FixtureRequest) -> Iterator[LedgerStore]:
    if request.param == "memory":
        yield InMemoryLedgerStore()
        return
    prefix = f"test_ledger_{uuid.uuid4().hex[:8]}"
    fs_store = FirestoreLedgerStore(collection_prefix=prefix)
    yield fs_store
    fs_store.delete_all_for_testing()


def _record(sequencer: LedgerSequencer, n: int) -> None:
    sequencer.record_event(LedgerEventType.APPROVAL_RECORDED, f"intent-{n}", {"n": n})


def test_empty_store_starts_at_genesis(store: LedgerStore) -> None:
    assert store.head() == (0, GENESIS_ANCHOR)
    assert store.list_entries() == []


def test_entries_chain_and_are_retrievable(store: LedgerStore) -> None:
    sequencer = LedgerSequencer(store=store)
    for n in range(3):
        _record(sequencer, n)
    entries = store.list_entries()
    assert [e.ledger_seq for e in entries] == [1, 2, 3]
    assert entries[0].prev_hash == GENESIS_ANCHOR
    assert all(entries[i].prev_hash == entries[i - 1].current_hash for i in (1, 2))
    assert store.get(2) == entries[1]
    assert store.get(99) is None
    assert store.head() == (3, entries[2].current_hash)


def test_concurrent_appends_are_gap_free_and_chained(store: LedgerStore) -> None:
    sequencer = LedgerSequencer(store=store)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: _record(sequencer, n), range(16)))
    entries = store.list_entries()
    assert [e.ledger_seq for e in entries] == list(range(1, 17))
    assert all(entries[i].prev_hash == entries[i - 1].current_hash for i in range(1, 16))


def test_a_new_sequencer_continues_the_same_chain(store: LedgerStore) -> None:
    _record(LedgerSequencer(store=store), 1)
    second = LedgerSequencer(store=store)
    assert second.current_seq == 1
    _record(second, 2)
    entries = store.list_entries()
    assert [e.ledger_seq for e in entries] == [1, 2]
    assert entries[1].prev_hash == entries[0].current_hash


def test_dev_default_is_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    from eios.ontology.actions.ledger_store import default_ledger_store

    monkeypatch.delenv("EIOS_PERSISTENCE", raising=False)
    monkeypatch.setenv("EIOS_ENVIRONMENT", "dev")
    assert isinstance(default_ledger_store(), InMemoryLedgerStore)


@pytest.mark.parametrize("environment", ["stage", "prod-like"])
def test_deployed_environments_refuse_in_memory(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    from eios.ontology.actions.ledger_store import default_ledger_store

    monkeypatch.delenv("EIOS_PERSISTENCE", raising=False)
    monkeypatch.setenv("EIOS_ENVIRONMENT", environment)
    with pytest.raises(RuntimeError, match="EIOS_PERSISTENCE"):
        default_ledger_store()
