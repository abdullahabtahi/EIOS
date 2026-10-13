"""Tests for User Story 4: Decision Policy Confidence & Playbook Prior Recalibration."""

from datetime import UTC, datetime

import pytest

from eios.flywheel.ledger import compute_record_lineage_hash
from eios.flywheel.models import DecisionOutcomeRecord, MilestoneStatus, PlaybookPolicyPrior
from eios.flywheel.schemas import validate_contract


def _create_mock_record(
    decision_id: str,
    action_type: str,
    actual_impact_60d: float,
    predicted_impact_60d: float = 1000.0,
) -> DecisionOutcomeRecord:
    now = datetime.now(UTC)
    h = compute_record_lineage_hash(
        decision_id=decision_id,
        intent_id=f"INT-{decision_id}",
        timestamp=now,
        entity_id="PARTNER-01",
        action_type=action_type,
        propensity_score=0.7,
        treatment_assigned=True,
    )
    return DecisionOutcomeRecord(
        decision_id=decision_id,
        intent_id=f"INT-{decision_id}",
        timestamp=now,
        service_name="churn_service",
        action_type=action_type,
        entity_type="Partner",
        entity_id="PARTNER-01",
        propensity_score=0.7,
        treatment_assigned=True,
        covariates={},
        predicted_impact_30d=500.0,
        actual_impact_30d=None,
        residual_30d=None,
        status_30d=MilestoneStatus.PENDING,
        predicted_impact_60d=predicted_impact_60d,
        actual_impact_60d=actual_impact_60d,
        residual_60d=actual_impact_60d - predicted_impact_60d,
        status_60d=MilestoneStatus.RECONCILED,
        predicted_impact_90d=1500.0,
        actual_impact_90d=None,
        residual_90d=None,
        status_90d=MilestoneStatus.PENDING,
        provenance_hash=h,
    )


def test_playbook_prior_updater():
    from eios.flywheel.playbook_priors import PlaybookPriorUpdater

    records = [
        _create_mock_record(
            f"d-{i}", "fee_tier_restructure", actual_impact_60d=1200.0 if i < 8 else -200.0
        )
        for i in range(10)
    ]
    # 8 positive outcomes out of 10 -> win-rate = 0.80

    updater = PlaybookPriorUpdater()
    prior = updater.update_prior(
        policy_id="POLICY-CHURN-01",
        action_type="fee_tier_restructure",
        records=records,
        horizon="60d",
    )

    assert isinstance(prior, PlaybookPolicyPrior)
    assert prior.empirical_win_rate == pytest.approx(0.80)
    assert prior.sample_observations == 10
    # Expected payoff: 8 * 1200 + 2 * (-200) = 9600 - 400 = 9200 / 10 = 920.0
    assert prior.expected_payoff_usd == pytest.approx(920.0)
    assert 0.0 <= prior.confidence_score <= 1.0


def test_playbook_prior_contract_validation():
    from eios.flywheel.playbook_priors import PlaybookPriorUpdater

    records = [
        _create_mock_record("d-1", "step_up_kyc", actual_impact_60d=500.0),
        _create_mock_record("d-2", "step_up_kyc", actual_impact_60d=600.0),
    ]
    updater = PlaybookPriorUpdater()
    prior = updater.update_prior(
        policy_id="POLICY-AML-02",
        action_type="step_up_kyc",
        records=records,
    )

    dumped = prior.model_dump(mode="json")
    assert validate_contract(dumped, "playbook-policy-prior") is True


def test_playbook_prior_empty_records():
    from eios.flywheel.playbook_priors import PlaybookPriorUpdater

    updater = PlaybookPriorUpdater()
    prior = updater.update_prior(
        policy_id="POLICY-EMPTY",
        action_type="unknown_action",
        records=[],
    )

    assert prior.sample_observations == 0
    assert prior.empirical_win_rate == 0.50
    assert prior.confidence_score == 0.0
    assert prior.expected_payoff_usd == 0.0
