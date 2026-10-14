"""The compliance views over the real decision ledger (spec 032): what the shelf writes is what the auditor reads."""

from typing import Any

import pytest

from eios.cockpit import compliance_view
from eios.cockpit.compliance import ComplianceExplorerService
from eios.cockpit.compliance_ledger import SIGNED_CHECKPOINT
from eios.cockpit.governance_runtime import GovernanceRuntime, build_governance_runtime
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import DataOrigin
from eios.ontology.omcp.port.readmodels import ReadModels
from tests.ontology.port.conftest import who

AUDITOR = who("compliance_auditor")
NOW = "2026-10-14T08:00:00+00:00"


@pytest.fixture
def runtime() -> GovernanceRuntime:
    return build_governance_runtime()


def _svc(rt: GovernanceRuntime) -> ComplianceExplorerService:
    return ComplianceExplorerService.over_ledger(rt.sequencer, rt.worm, rt.hub)


def _hold(rt: GovernanceRuntime, *, approve: bool) -> str:
    token = rt.hub.propose_action(
        action_type="HoldWithdrawal",
        parameters={"txn_id": "W-84920-1", "reason": "income discrepancy", "entity_id": "CR84920"},
        evidence_refs=["case_aml_CR84920"],
        requester_agent_id="analyst-1",
        require_dual_approval=True,
    )
    if approve:
        rt.hub.approve_action(token.intent_id, approver_id="approver-1", role="AML_INVESTIGATOR")
        rt.hub.approve_action(token.intent_id, approver_id="approver-2", role="COMPLIANCE_HEAD")
    return token.intent_id


def test_an_empty_ledger_reads_as_empty_not_as_a_canned_sequence(
    runtime: GovernanceRuntime,
) -> None:
    svc = _svc(runtime)
    assert svc.get_ledger_timeline() == []
    assert svc.get_four_eyes_approval_log() == []
    assert svc.get_worm_compliance_proofs() == []
    v = svc.verify_hash_chain_interactive()
    assert v["total_entries_verified"] == 0 and v["is_chain_unbroken"] is True


def test_a_staged_and_approved_hold_shows_in_the_timeline_and_the_approval_log(
    runtime: GovernanceRuntime,
) -> None:
    intent = _hold(runtime, approve=True)
    svc = _svc(runtime)
    rows = svc.get_ledger_timeline()
    assert [r["ledger_seq"] for r in rows] == [1, 2, 3]
    assert [r["event_type"] for r in rows] == [
        "PROPOSAL_CREATED",
        "APPROVAL_RECORDED",
        "APPROVAL_RECORDED",
    ]
    assert [r["actor_id"] for r in rows] == ["analyst-1", "approver-1", "approver-2"]
    assert rows[1]["prev_hash"] == rows[0]["current_hash"]
    (log,) = svc.get_four_eyes_approval_log()
    assert log["intent_id"] == intent and log["target_entity_id"] == "CR84920"
    assert log["first_approver"]["role"] == "AML_INVESTIGATOR"
    assert log["second_approver"]["role"] == "COMPLIANCE_HEAD"
    assert svc.verify_hash_chain_interactive()["total_entries_verified"] == 3


def test_a_pending_intent_has_no_sign_offs_yet(runtime: GovernanceRuntime) -> None:
    _hold(runtime, approve=False)
    (log,) = _svc(runtime).get_four_eyes_approval_log()
    assert log["first_approver"] is None and log["second_approver"] is None


def test_checkpoints_are_signed_anchors_and_mark_covered_entries(
    runtime: GovernanceRuntime,
) -> None:
    _hold(runtime, approve=False)
    runtime.worm.create_checkpoint()
    _hold(runtime, approve=False)
    svc = _svc(runtime)
    (proof,) = svc.get_worm_compliance_proofs()
    assert proof["compliance_lock_mode"] == SIGNED_CHECKPOINT and proof["chain_head_seq"] == 1
    assert [r["is_worm_anchored"] for r in svc.get_ledger_timeline()] == [True, False]


def test_the_port_reads_the_same_ledger_and_says_it_is_live(runtime: GovernanceRuntime) -> None:
    intent = _hold(runtime, approve=True)
    port = build_port(ReadModels.over(ReadModels.default().aml, compliance=_svc(runtime)))
    status = port.call(AUDITOR, "get_intent_status", {"intent_id": intent})
    assert status.error is None, status.error
    got: dict[str, Any] = status.payload()
    assert got["status"] and got["second_approver_role"] == "COMPLIANCE_HEAD"
    timeline = port.call(AUDITOR, "get_ledger_timeline", {}).payload()
    assert timeline["data_origin"] == DataOrigin.LIVE.value and len(timeline["entries"]) == 3
    chain = port.call(AUDITOR, "verify_chain", {}).payload()
    assert chain["is_simulated"] is False and chain["total_entries_verified"] == 3


def test_the_workstation_payload_says_when_no_checkpoint_exists(
    runtime: GovernanceRuntime,
) -> None:
    _hold(runtime, approve=False)
    triage, dossier, canvas = compliance_view.workstation(_svc(runtime), NOW)
    assert [t["entity_id"] for t in triage] == ["SEQ-1"]
    assert "No signed checkpoint" in dossier["sections"][0]["narrative_text"]
    assert canvas["payload"]["worm_proof"] is None and canvas["payload"]["chain_valid"] is True
    payload = compliance_view.ledger_payload(_svc(runtime))
    assert payload["is_simulated"] is False and payload["entries"][0]["ledger_seq"] == 1
