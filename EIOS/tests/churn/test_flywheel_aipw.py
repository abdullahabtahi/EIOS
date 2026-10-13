"""Unit tests for Governed Retention Playbooks and Doubly Robust AIPW Flywheel (T027 / US5)."""

import numpy as np
import pandas as pd
import pytest

from eios.churn.flywheel import AIPWCausalEstimator, PlaybookRecalibrator
from eios.churn.models import ActionIntentProposal, DecisionOutcomeRecord
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.intent_hub import (
    ActionIntentHub,
    ActionSeverity,
    ActionStatus,
)
from eios.ontology.actions.signer import LocalDevActionSigner


def test_action_intent_token_ecdsa_signature():
    """Verify LaunchRetentionPlaybook generates a valid KMS ECDSA P-256 signed ActionIntentToken."""
    signer = LocalDevActionSigner()
    hub = ActionIntentHub(signer=signer)

    proposal = ActionIntentProposal(
        partner_ids=["P-CHURN-DRIFT"],
        playbook_id="Offer_Tier_Upgrade",
        budget=5000.0,
        rationale="Partner exhibits 40% login decay and competitor revshare inquiry.",
        evidence_refs=["DP6:partner_360", "DP10:partner_comms"],
        propensity_score=0.75,
        causal_context={"regional_competitor": "XM", "spread_diff": 0.5},
    )

    token = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={
            "partner_ids": proposal.partner_ids,
            "playbook_id": proposal.playbook_id,
            "budget": proposal.budget,
        },
        evidence_refs=proposal.evidence_refs,
        requester_agent_id="ChurnRadarSpecialist",
        propensity_score=proposal.propensity_score,
        causal_context=proposal.causal_context,
    )

    assert token.action_type == "LaunchRetentionPlaybook"
    assert token.status == ActionStatus.PENDING
    assert token.severity == ActionSeverity.MEDIUM
    assert token.signature != ""
    assert token.propensity_score == 0.75

    # Verify cryptographic signature
    is_valid = signer.verify_token(token)
    assert is_valid is True

    # Tamper with token payload and verify rejection
    tampered_token = token.model_copy(deep=True)
    tampered_token.parameters["budget"] = 99999.0
    assert signer.verify_token(tampered_token) is False


def test_aipw_estimator_unbiases_confounding_by_indication():
    """Verify Doubly Robust AIPW overcomes Simpson's paradox where naive difference in means is negative."""
    np.random.seed(42)
    n = 1000

    # Covariate X: partner baseline risk (1 = high risk, 0 = low risk)
    # High risk partners have lower baseline revenue
    X = np.random.binomial(1, 0.5, size=n)
    baseline_revenue = np.where(X == 1, 5000.0, 20000.0)

    # Confounded treatment assignment: managers treat high risk partners far more often
    # P(W=1 | X=1) = 0.80, P(W=1 | X=0) = 0.20
    propensity = np.where(X == 1, 0.80, 0.20)
    W = np.random.binomial(1, propensity, size=n)

    # True treatment effect tau = +4000.0 retained revenue
    true_tau = 4000.0
    noise = np.random.normal(0, 500.0, size=n)
    observed_revenue = baseline_revenue + W * true_tau + noise

    df = pd.DataFrame(
        {
            "treatment_assigned": W,
            "observed_retained_revenue_60d": observed_revenue,
            "propensity_score": propensity,
            "risk_covariate": X,
        }
    )

    # Naive estimator
    mean_treated = df[df["treatment_assigned"] == 1]["observed_retained_revenue_60d"].mean()
    mean_control = df[df["treatment_assigned"] == 0]["observed_retained_revenue_60d"].mean()
    naive_ate = mean_treated - mean_control

    # Naive estimate is severely negative due to confounding by indication
    assert naive_ate < 0, f"Naive ATE should be negative due to confounding, got {naive_ate}"

    # AIPW Doubly Robust Estimator
    estimator = AIPWCausalEstimator()
    res = estimator.estimate_ate(df, feature_cols=["risk_covariate"])

    # AIPW accurately recovers positive treatment effect near true_tau (+4000)
    assert res["ate"] > 3000.0
    assert res["ate"] < 5000.0
    assert res["is_significant"] is True
    assert res["ci_lower"] < true_tau < res["ci_upper"]


def test_playbook_recalibration_from_hot_state():
    """Verify PlaybookRecalibrator updates selection weights based on ledger outcomes."""
    engine = HotStateEngine(":memory:")
    recalibrator = PlaybookRecalibrator(engine)

    # Record outcomes for two playbooks:
    # PB-A (effective, ATE > 0) and PB-B (ineffective, ATE <= 0)
    np.random.seed(42)
    for i in range(100):
        # PB-A: treated gets +5000
        w_a = int(np.random.rand() < 0.6)
        rev_a = 10000.0 + (5000.0 if w_a == 1 else 0.0) + np.random.normal(0, 200)
        recalibrator.record_outcome(
            DecisionOutcomeRecord(
                outcome_id=f"OUT-A-{i}",
                intent_id=f"INT-A-{i}",
                partner_id=f"P-A-{i}",
                playbook_id="Offer_Tier_Upgrade",
                treatment_assigned=w_a,
                propensity_score=0.6,
                observed_retained_revenue_60d=rev_a,
                actual_churn_60d=False,
            )
        )

        # PB-B: treated gets -1000 (churn acceleration)
        w_b = int(np.random.rand() < 0.5)
        rev_b = 8000.0 + (-1000.0 if w_b == 1 else 0.0) + np.random.normal(0, 200)
        recalibrator.record_outcome(
            DecisionOutcomeRecord(
                outcome_id=f"OUT-B-{i}",
                intent_id=f"INT-B-{i}",
                partner_id=f"P-B-{i}",
                playbook_id="Standard_Email_Outreach",
                treatment_assigned=w_b,
                propensity_score=0.5,
                observed_retained_revenue_60d=rev_b,
                actual_churn_60d=True if w_b == 1 else False,
            )
        )

    weights = recalibrator.recalibrate_playbook_weights()

    assert "Offer_Tier_Upgrade" in weights
    assert "Standard_Email_Outreach" in weights
    assert pytest.approx(sum(weights.values()), rel=1e-3) == 1.0
    # Effective playbook receives substantially higher weight
    assert weights["Offer_Tier_Upgrade"] > weights["Standard_Email_Outreach"]
