"""Showing the shelf costs a fixed number of store reads, not a few per card.

On Firestore every read is a network round trip (about a quarter of a second from a laptop). The workstation state
request once read each card's intent twice, so 22 cards took 44 sequential reads and about 11 s: over the web proxy's
8 s limit, which then showed the replay.
"""

from __future__ import annotations

from typing import Any

from eios.cockpit.governance_shelf import GovernedActionShelf
from eios.ontology.actions.intent_hub import ActionIntentHub
from eios.ontology.actions.ledger_store import InMemoryLedgerStore
from eios.ontology.actions.record_store import InMemoryRecordStore
from eios.ontology.actions.sequencer import LedgerSequencer
from eios.ontology.actions.signer import LocalDevActionSigner
from eios.ontology.actions.sink import SimulatedWriteBackSink

PARAMS = {"client_id": "C-1", "reason_code": "TEST"}


class CountingStore(InMemoryRecordStore):
    def __init__(self) -> None:
        super().__init__()
        self.gets = 0
        self.lists = 0

    def get(self, key: str) -> Any:
        self.gets += 1
        return super().get(key)

    def list(self) -> Any:
        self.lists += 1
        return super().list()


def _shelf(cards: int) -> tuple[GovernedActionShelf, ActionIntentHub, CountingStore]:
    tokens = CountingStore()
    signer = LocalDevActionSigner()
    sequencer = LedgerSequencer(store=InMemoryLedgerStore())
    hub = ActionIntentHub(
        signer=signer,
        sequencer=sequencer,
        sink=SimulatedWriteBackSink(sequencer=sequencer),
        token_records=tokens,
        nonce_records=InMemoryRecordStore(),
    )
    for i in range(cards):
        hub.propose_action("FreezeAccount", PARAMS, [f"ev-{i}"], requester_agent_id="alice")
    tokens.gets = tokens.lists = 0
    return GovernedActionShelf(intent_hub=hub, signer=signer), hub, tokens


def test_finding_one_intent_is_one_read() -> None:
    _, hub, tokens = _shelf(1)
    intent_id = hub.list_tokens()[0].intent_id
    tokens.gets = tokens.lists = 0
    assert hub.find(intent_id) is not None
    assert tokens.gets == 1
    assert hub.find("missing") is None
    assert tokens.gets == 2


def test_listing_the_shelf_with_its_tokens_is_one_list_and_no_per_card_reads() -> None:
    shelf, _, tokens = _shelf(22)
    pairs = shelf.list_cards_with_tokens()
    assert len(pairs) == 22
    assert all(card.intent_id == token.intent_id for card, token in pairs)
    assert tokens.lists == 1
    assert tokens.gets == 0


def test_the_pairs_match_the_cards_and_tokens_listed_separately() -> None:
    shelf, hub, _ = _shelf(3)
    pairs = shelf.list_cards_with_tokens()
    assert [c.intent_id for c, _ in pairs] == [c.intent_id for c in shelf.list_cards()]
    assert [t.intent_id for _, t in pairs] == [t.intent_id for t in hub.list_tokens()]
