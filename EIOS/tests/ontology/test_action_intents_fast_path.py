"""Tests for ActionIntentHub dual-approval policy fast-path and auto-staging (FM-3 Countermeasure)."""

import pytest

from eios.ontology.actions.intent_hub import (
    ActionIntentHub,
    ActionSeverity,
    ActionStatus,
    FourEyesApprovalRequiredError,
)


def test_fast_path_for_low_budget_medium_severity():
    hub = ActionIntentHub()

    # LaunchRetentionPlaybook with budget $1,200 <= $2,500 threshold
    token = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={"partner_ids": ["P-1"], "playbook_id": "FAST_RETAIN", "budget": 1200.0},
        evidence_refs=["EVID-1"],
    )

    assert token.severity == ActionSeverity.MEDIUM
    assert token.requires_dual_approval is False
    assert "FAST_PATH_ELIGIBLE" in token.policy_tags

    # Single approval should immediately transition to APPROVED
    approved_token = hub.approve_action(token.intent_id, approver_id="LEAD_1", role="PARTNER_LEAD")
    assert approved_token.status == ActionStatus.APPROVED

    # Execution succeeds without requiring a second approver
    executed_token = hub.execute_action(token.intent_id)
    assert executed_token.status == ActionStatus.EXECUTED


def test_dual_approval_mandated_for_high_budget_medium_severity():
    hub = ActionIntentHub()

    # LaunchRetentionPlaybook with budget $10,000 > $2,500 threshold
    token = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={"partner_ids": ["P-1"], "playbook_id": "EXPENSIVE_RETAIN", "budget": 10000.0},
        evidence_refs=["EVID-1"],
    )

    assert token.severity == ActionSeverity.MEDIUM
    assert token.requires_dual_approval is True
    assert "DUAL_APPROVAL_MANDATORY" in token.policy_tags

    # Single approval remains PENDING
    hub.approve_action(token.intent_id, approver_id="LEAD_1", role="PARTNER_LEAD")
    assert hub.get_status(token.intent_id).status == ActionStatus.PENDING

    with pytest.raises(FourEyesApprovalRequiredError):
        hub.execute_action(token.intent_id)

    # Second approval transitions to APPROVED
    hub.approve_action(token.intent_id, approver_id="HEAD_1", role="HEAD_OF_PARTNERSHIPS")
    assert hub.get_status(token.intent_id).status == ActionStatus.APPROVED

    # Execution now succeeds
    executed_token = hub.execute_action(token.intent_id)
    assert executed_token.status == ActionStatus.EXECUTED


def test_auto_stage_low_risk_actions():
    hub = ActionIntentHub()

    # Create low-risk action (ReviewSpreadPricing is LOW severity)
    token_low = hub.propose_action(
        action_type="ReviewSpreadPricing",
        parameters={"symbol": "EURUSD", "target_spread_pips": 1.2},
        evidence_refs=["EVID-SPREAD-1"],
    )

    # Create medium action with small budget ($400)
    token_med_small = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={"partner_ids": ["P-2"], "playbook_id": "MICRO_BONUS", "budget": 400.0},
        evidence_refs=["EVID-MICRO"],
    )

    # Create high-severity action (FreezeAccount)
    token_high = hub.propose_action(
        action_type="FreezeAccount",
        parameters={"client_id": "C-99", "reason_code": "FRAUD"},
        evidence_refs=["EVID-AML"],
    )

    # Trigger auto-staging
    staged_ids = hub.auto_stage_low_risk_actions(max_budget=1000.0)

    assert token_low.intent_id in staged_ids
    assert token_med_small.intent_id in staged_ids
    assert token_high.intent_id not in staged_ids

    assert hub.get_status(token_low.intent_id).status == ActionStatus.APPROVED
    assert hub.get_status(token_med_small.intent_id).status == ActionStatus.APPROVED
    assert hub.get_status(token_high.intent_id).status == ActionStatus.PENDING
