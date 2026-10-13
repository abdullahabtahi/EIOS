"""Integration tests for investigation dossier assembly and governed Action Intents (T032 / US6).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US6, FR-010, FR-011, FR-012, FR-013, SC-005)
- .specify/memory/constitution.md (Principle II)
"""

import pytest

from eios.fraud.dossier import FraudDossierAssembler
from eios.ontology.actions.intent_hub import (
    ActionIntentHub,
    ActionSeverity,
    ActionStatus,
    FourEyesApprovalRequiredError,
)


def test_dossier_assembler_creates_sanitized_case() -> None:
    assembler = FraudDossierAssembler()
    case = assembler.assemble_dossier(
        partner_id="P-FRAUD-01",
        is_replay_fallback=False,
    )

    assert case.partner_id == "P-FRAUD-01"
    assert case.status == "OPEN"
    assert case.recommended_action in [
        "ClawbackCommission",
        "SuspendPartner",
        "AdjustPartnerTier",
        "ReviewAudit",
    ]
    assert "P-FRAUD-01" in case.narrative_summary
    # Check that inflammatory terms are not present
    assert "criminal ring" not in case.narrative_summary
    assert "fraudster" not in case.narrative_summary


def test_clawback_action_intent_requires_dual_approval() -> None:
    """Constitution Principle II: ClawbackCommission has HIGH severity and requires dual 4-eyes approval."""
    hub = ActionIntentHub()

    # Propose ClawbackCommission
    token = hub.propose_action(
        action_type="ClawbackCommission",
        parameters={"partner_id": "P-FRAUD-01", "period": "2026-Q3", "amount": 15000.0},
        evidence_refs=["trading_activity/PAIR-01", "commission_ledger/COM-01"],
        requester_agent_id="PartnerFraudSpecialist",
    )

    assert token.severity == ActionSeverity.HIGH
    assert token.requires_dual_approval is True
    assert token.status == ActionStatus.PENDING
    assert token.signature is not None

    # First approver signs
    token = hub.approve_action(
        token.intent_id, approver_id="officer_alice", role="ComplianceOfficer"
    )
    assert token.status == ActionStatus.PENDING
    assert len(token.approvals) == 1

    # Second approver signs
    token = hub.approve_action(token.intent_id, approver_id="officer_bob", role="SeniorMLRO")
    assert token.status == ActionStatus.APPROVED
    assert len(token.approvals) == 2


def test_single_approver_cannot_bypass_four_eyes_on_high_severity() -> None:
    """A single approver cannot execute high severity action without second distinct approver."""
    from eios.ontology.actions.intent_hub import InvalidActionParameterError

    hub = ActionIntentHub()

    token = hub.propose_action(
        action_type="SuspendPartner",
        parameters={"partner_id": "P-FRAUD-01", "scope": "ALL_SUB_ACCOUNTS"},
        evidence_refs=["case/CASE-FRAUD-01"],
        requester_agent_id="PartnerFraudSpecialist",
    )

    # First approver
    token = hub.approve_action(
        token.intent_id, approver_id="officer_alice", role="ComplianceOfficer"
    )

    # Attempt execution with only 1 approval -> raises FourEyesApprovalRequiredError
    with pytest.raises(FourEyesApprovalRequiredError):
        hub.execute_action(token.intent_id)

    # Same approver cannot be second approver
    with pytest.raises(InvalidActionParameterError, match="already approved"):
        hub.approve_action(token.intent_id, approver_id="officer_alice", role="ComplianceOfficer")
