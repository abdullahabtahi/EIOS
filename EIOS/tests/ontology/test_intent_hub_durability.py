"""Intent hub state lives in a RecordStore: it survives a new hub instance and rejects replays and lost updates."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from eios.ontology.actions.intent_hub import ActionIntentHub, NonceReplayError
from eios.ontology.actions.models import ActionStatus
from eios.ontology.actions.record_store import InMemoryRecordStore
from eios.ontology.actions.signer import LocalDevActionSigner

PARAMS = {"client_id": "C-1", "reason_code": "TEST"}


def _hub(
    tokens: InMemoryRecordStore, nonces: InMemoryRecordStore, signer: LocalDevActionSigner
) -> ActionIntentHub:
    return ActionIntentHub(signer=signer, token_records=tokens, nonce_records=nonces)


@pytest.fixture
def shared() -> tuple[InMemoryRecordStore, InMemoryRecordStore, LocalDevActionSigner]:
    return InMemoryRecordStore(), InMemoryRecordStore(), LocalDevActionSigner()


def test_proposed_token_is_visible_to_a_second_hub(shared) -> None:
    first, second = _hub(*shared), _hub(*shared)
    token = first.propose_action("FreezeAccount", PARAMS, ["ev-1"])
    assert second.get_status(token.intent_id).intent_id == token.intent_id
    assert second.get_status(token.intent_id).signature == token.signature


def test_approval_on_one_hub_is_seen_by_the_other(shared) -> None:
    first, second = _hub(*shared), _hub(*shared)
    token = first.propose_action("FreezeAccount", PARAMS, ["ev-1"])
    second.approve_action(token.intent_id, "alice", "ANALYST")
    assert [a.approver_id for a in first.get_status(token.intent_id).approvals] == ["alice"]


def test_concurrent_distinct_approvals_are_both_recorded(shared) -> None:
    hubs = [_hub(*shared) for _ in range(2)]
    token = hubs[0].propose_action("FreezeAccount", PARAMS, ["ev-1"])
    approvers = [("alice", "ANALYST"), ("bob", "COMPLIANCE_HEAD")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda i: hubs[i].approve_action(token.intent_id, *approvers[i]), range(2)))
    final = hubs[0].get_status(token.intent_id)
    assert sorted(a.approver_id for a in final.approvals) == ["alice", "bob"]
    assert final.status == ActionStatus.APPROVED


def test_nonce_replay_is_rejected_across_instances(shared) -> None:
    first, second = _hub(*shared), _hub(*shared)
    first._register_nonce("abc")
    with pytest.raises(NonceReplayError):
        second._register_nonce("abc")


def test_stale_write_is_rejected_not_silently_applied(shared) -> None:
    from eios.ontology.actions.intent_hub import ConcurrentModificationError

    hub = _hub(*shared)
    token = hub.propose_action("FreezeAccount", PARAMS, ["ev-1"])
    stale = hub.get_status(token.intent_id)
    fresh = hub.get_status(token.intent_id)
    fresh.policy_tags.append("first-writer")
    hub._persist_token(fresh)
    stale.policy_tags.append("second-writer")
    with pytest.raises(ConcurrentModificationError):
        hub._persist_token(stale)


def test_caller_can_raise_but_not_lower_the_approval_bar(shared) -> None:
    hub = _hub(*shared)
    low = hub.propose_action(
        "ReviewSpreadPricing", {"symbol": "EURUSD", "target_spread_pips": 1.2}, ["ev"]
    )
    assert low.requires_dual_approval is False
    raised = hub.propose_action(
        "ReviewSpreadPricing",
        {"symbol": "EURUSD", "target_spread_pips": 1.2},
        ["ev"],
        require_dual_approval=True,
    )
    assert raised.requires_dual_approval is True
    high = hub.propose_action("FreezeAccount", PARAMS, ["ev"], require_dual_approval=False)
    assert high.requires_dual_approval is True


def test_a_proposer_never_approves_their_own_intent(shared) -> None:
    from eios.ontology.actions.intent_hub import FourEyesViolationError

    hub = _hub(*shared)
    token = hub.propose_action(
        "ReviewSpreadPricing",
        {"symbol": "EURUSD", "target_spread_pips": 1.2},
        ["ev"],
        requester_agent_id="alice",
    )
    with pytest.raises(FourEyesViolationError):
        hub.approve_action(token.intent_id, "alice", "ANALYST")
