"""The shelf in hub mode presents the hub's real state: real signature checks, ledgered transitions, no swallowed errors."""

import pytest

from eios.cockpit.governance_shelf import GovernedActionShelf
from eios.ontology.actions.intent_hub import ActionIntentHub, FourEyesViolationError
from eios.ontology.actions.ledger_store import InMemoryLedgerStore
from eios.ontology.actions.models import LedgerEventType
from eios.ontology.actions.record_store import InMemoryRecordStore
from eios.ontology.actions.sequencer import LedgerSequencer
from eios.ontology.actions.signer import LocalDevActionSigner
from eios.ontology.actions.sink import SimulatedWriteBackSink

PARAMS = {"client_id": "C-1", "reason_code": "TEST"}


def _runtime(tokens=None, nonces=None, ledger=None):
    signer = LocalDevActionSigner()
    sequencer = LedgerSequencer(store=ledger or InMemoryLedgerStore())
    hub = ActionIntentHub(
        signer=signer,
        sequencer=sequencer,
        sink=SimulatedWriteBackSink(sequencer=sequencer),
        token_records=tokens or InMemoryRecordStore(),
        nonce_records=nonces or InMemoryRecordStore(),
    )
    return hub, GovernedActionShelf(intent_hub=hub, signer=signer), sequencer


def test_card_reports_a_real_signature_check() -> None:
    hub, shelf, _ = _runtime()
    token = hub.propose_action("FreezeAccount", PARAMS, ["ev-1"], requester_agent_id="alice")
    assert shelf.present_card(token).kms_signature_verified is True


def test_tampered_token_is_reported_unverified() -> None:
    hub, shelf, _ = _runtime()
    token = hub.propose_action("FreezeAccount", PARAMS, ["ev-1"], requester_agent_id="alice")
    forged = hub.get_status(token.intent_id)
    forged.parameters = {**forged.parameters, "client_id": "C-999"}
    hub._persist_token(forged)
    assert shelf.present_card(hub.get_status(token.intent_id)).kms_signature_verified is False


def test_a_made_up_signature_is_not_verified() -> None:
    hub, shelf, _ = _runtime()
    token = hub.propose_action("FreezeAccount", PARAMS, ["ev-1"], requester_agent_id="alice")
    fake = token.model_copy(update={"signature": "ZmFrZQ=="})
    assert shelf.present_card(fake).kms_signature_verified is False


def test_full_flow_is_ledgered_end_to_end() -> None:
    hub, shelf, sequencer = _runtime()
    token = hub.propose_action("FreezeAccount", PARAMS, ["ev-1"], requester_agent_id="alice")
    shelf.submit_approval(token.intent_id, "bob", "ANALYST")
    card = shelf.submit_approval(token.intent_id, "carol", "COMPLIANCE_HEAD")
    assert card.status == "APPROVED"
    receipt = shelf.execute_action(token.intent_id)
    assert receipt["status"] == "COMMITTED"
    events = [e.event_type for e in sequencer.entries]
    assert events.count(LedgerEventType.PROPOSAL_CREATED) == 1
    assert events.count(LedgerEventType.APPROVAL_RECORDED) == 2
    assert LedgerEventType.ACTION_EXECUTED in events


def test_initiator_cannot_approve_their_own_intent() -> None:
    hub, shelf, _ = _runtime()
    token = hub.propose_action("FreezeAccount", PARAMS, ["ev-1"], requester_agent_id="alice")
    with pytest.raises(FourEyesViolationError):
        shelf.submit_approval(token.intent_id, "alice", "ANALYST")


def test_hub_errors_are_not_swallowed() -> None:
    _, shelf, _ = _runtime()
    with pytest.raises(KeyError):
        shelf.submit_approval("missing", "bob", "ANALYST")


def test_second_shelf_on_shared_stores_sees_the_same_cards() -> None:
    tokens, nonces, ledger = InMemoryRecordStore(), InMemoryRecordStore(), InMemoryLedgerStore()
    hub_a, shelf_a, _ = _runtime(tokens, nonces, ledger)
    _, shelf_b, _ = _runtime(tokens, nonces, ledger)
    token = hub_a.propose_action("FreezeAccount", PARAMS, ["ev-1"], requester_agent_id="alice")
    assert [c.intent_id for c in shelf_b.list_cards()] == [token.intent_id]
    assert shelf_b.get_token(token.intent_id) is not None


def test_abort_is_recorded() -> None:
    hub, shelf, sequencer = _runtime()
    token = hub.propose_action("FreezeAccount", PARAMS, ["ev-1"], requester_agent_id="alice")
    assert shelf.abort_action(token.intent_id, "operator cancelled").status == "ABORTED"
    assert LedgerEventType.ACTION_ABORTED in [e.event_type for e in sequencer.entries]
