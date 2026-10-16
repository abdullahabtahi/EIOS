"""The compliance workstation reads each ledger collection once per request, not once per section.

On Firestore every listing is a network round trip. The request used to list the intents three times, the WORM
checkpoints three times and the ledger entries twice, which put the compliance workstation at 3-5 s.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

import pytest

from eios.cockpit import compliance_view
from eios.cockpit.compliance import ComplianceExplorerService
from eios.cockpit.governance_runtime import GovernanceRuntime, build_governance_runtime

NOW = "2026-10-14T08:00:00+00:00"


def _counting(counts: Counter[str], name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        counts[name] += 1
        return fn(*args, **kwargs)

    return wrapper


@pytest.fixture
def staged() -> tuple[GovernanceRuntime, Counter[str]]:
    rt = build_governance_runtime()
    token = rt.hub.propose_action(
        action_type="HoldWithdrawal",
        parameters={"txn_id": "W-1", "reason": "income discrepancy", "entity_id": "CR84920"},
        evidence_refs=["case"],
        requester_agent_id="analyst-1",
        require_dual_approval=True,
    )
    rt.hub.approve_action(token.intent_id, approver_id="a-1", role="AML_INVESTIGATOR")
    rt.worm.create_checkpoint()
    counts: Counter[str] = Counter()
    rt.hub.list_tokens = _counting(counts, "tokens", rt.hub.list_tokens)  # type: ignore[method-assign]
    rt.worm.get_checkpoints = _counting(counts, "checkpoints", rt.worm.get_checkpoints)  # type: ignore[method-assign]
    store = rt.sequencer._store
    store.list_entries = _counting(counts, "entries", store.list_entries)  # type: ignore[method-assign]
    return rt, counts


def _svc(rt: GovernanceRuntime) -> ComplianceExplorerService:
    return ComplianceExplorerService.over_ledger(rt.sequencer, rt.worm, rt.hub)


def test_the_workstation_lists_each_collection_once(
    staged: tuple[GovernanceRuntime, Counter[str]],
) -> None:
    rt, counts = staged
    compliance_view.workstation(_svc(rt), NOW)
    assert counts == {"tokens": 1, "checkpoints": 1, "entries": 1}


def test_the_ledger_endpoint_payload_lists_each_collection_once(
    staged: tuple[GovernanceRuntime, Counter[str]],
) -> None:
    rt, counts = staged
    compliance_view.ledger_payload(_svc(rt))
    assert counts == {"tokens": 1, "checkpoints": 1, "entries": 1}


def test_the_single_read_payload_equals_the_separate_reads(
    staged: tuple[GovernanceRuntime, Counter[str]],
) -> None:
    rt, _ = staged
    svc = _svc(rt)
    payload = compliance_view.ledger_payload(svc)
    assert payload["entries"] == list(reversed(svc.get_ledger_timeline(start_seq=1, limit=10_000)))
    assert payload["approvals"] == list(reversed(svc.get_four_eyes_approval_log()))
    assert payload["checkpoints"] == svc.get_worm_compliance_proofs()
    verification = svc.verify_hash_chain_interactive()
    for key in (
        "total_entries_verified",
        "is_chain_unbroken",
        "chain_head_hash",
        "worm_anchors_matched",
    ):
        assert payload["verification"][key] == verification[key]


def test_intents_the_caller_already_listed_are_not_listed_again(
    staged: tuple[GovernanceRuntime, Counter[str]],
) -> None:
    rt, counts = staged
    listed = rt.hub.list_tokens()
    counts.clear()
    triage, _, _ = compliance_view.workstation(_svc(rt), NOW, tokens=listed)
    assert counts == {"checkpoints": 1, "entries": 1}
    assert triage  # the view is still built


def test_the_workstation_state_lists_the_intents_once(monkeypatch: pytest.MonkeyPatch) -> None:
    from eios.cockpit import server

    gov = server.governance
    monkeypatch.setattr(
        server,
        "compliance_svc",
        ComplianceExplorerService.over_ledger(gov.sequencer, gov.worm, gov.hub),
    )
    counts: Counter[str] = Counter()
    monkeypatch.setattr(gov.hub, "list_tokens", _counting(counts, "tokens", gov.hub.list_tokens))
    server._build_contract_state("compliance_auditor")
    assert counts["tokens"] == 1


def test_a_checkpoint_past_the_entries_read_triggers_one_reread(
    staged: tuple[GovernanceRuntime, Counter[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    rt, _ = staged
    real = rt.sequencer._store.list_entries
    total = len(real())
    listings: list[int] = []

    def skewed() -> Any:
        rows = real()
        listings.append(len(rows))
        # the first listing is taken before the checkpoint's entries landed
        return rows[:1] if len(listings) == 1 else rows

    monkeypatch.setattr(rt.sequencer._store, "list_entries", skewed)
    read = _svc(rt).read_ledger()
    assert read is not None and len(read.entries) == total
    assert len(listings) == 2
