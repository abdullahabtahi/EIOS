"""Unit and causal estimation tests for Decision Outcomes Ledger and Doubly Robust AIPW (US5)."""

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.intent_hub import ActionIntentHub
from eios.ontology.actions.models import DecisionOutcomeRecord
from eios.ontology.actions.outcomes import DecisionOutcomesStore
import numpy as np
import pytest


def test_decision_outcomes_store_records_proposal_and_overrides():
    engine = HotStateEngine(db_path=":memory:")
    store = DecisionOutcomesStore(hot_state_engine=engine)

    rec = store.record_decision(
        intent_id="INTENT-CAUSAL-1",
        entity_id="P-501",
        action_type="LaunchRetentionPlaybook",
        treatment_assigned=1,
        propensity_score=0.82,
        causal_features={"partner_tier": 2.0, "churn_hazard": 0.68, "monthly_gmv": 125000.0},
        manager_override_flag=True,
        override_reason="Strategic VIP account - reduced budget from $2500 to $1200",
    )

    assert isinstance(rec, DecisionOutcomeRecord)
    assert rec.intent_id == "INTENT-CAUSAL-1"
    assert rec.propensity_score == 0.82
    assert rec.manager_override_flag is True
    assert rec.reconciled_at is None

    # Verify hot state
    cursor = engine.get_cursor()
    row = cursor.execute(
        "SELECT outcome_id, intent_id, treatment_assigned, propensity_score, manager_override_flag FROM decision_outcomes_ledger WHERE outcome_id = ?",
        [rec.outcome_id],
    ).fetchone()

    assert row is not None
    assert row[1] == "INTENT-CAUSAL-1"
    assert row[2] == 1
    assert abs(row[3] - 0.82) < 1e-4
    assert row[4] is True


def test_decision_outcomes_multi_horizon_reconciliation():
    engine = HotStateEngine(db_path=":memory:")
    store = DecisionOutcomesStore(hot_state_engine=engine)

    rec = store.record_decision(
        intent_id="INTENT-RECON-1",
        entity_id="C-902",
        action_type="HoldWithdrawal",
        treatment_assigned=1,
        propensity_score=0.94,
        causal_features={"velocity": 5.0, "turnover": 0.01},
    )

    reconciled = store.reconcile_outcomes(
        outcome_id=rec.outcome_id,
        observed_retained_revenue_30d=15000.0,
        observed_retained_revenue_60d=32000.0,
        actual_churn_60d=False,
        clawback_recovered_usd_90d=8500.0,
    )

    assert reconciled.observed_retained_revenue_30d == 15000.0
    assert reconciled.observed_retained_revenue_60d == 32000.0
    assert reconciled.actual_churn_60d is False
    assert reconciled.clawback_recovered_usd_90d == 8500.0
    assert reconciled.reconciled_at is not None


def test_doubly_robust_aipw_debiasing_synthetic_experiment():
    store = DecisionOutcomesStore()
    np.random.seed(42)
    n = 1000

    # True treatment effect tau = +5000.0 USD retained revenue
    true_tau = 5000.0

    # Confounder X: baseline risk (accounts with higher risk are more likely to be treated)
    x = np.random.normal(loc=50.0, scale=15.0, size=n)

    # Confounded propensity: logit(e) = 0.08 * (x - 50)
    logits = 0.08 * (x - 50.0)
    e = 1.0 / (1.0 + np.exp(-logits))
    # Clip propensity to avoid division by near-zero
    e = np.clip(e, 0.05, 0.95)

    # Treatment assignment W ~ Bernoulli(e)
    w = np.random.binomial(1, e)

    # Untreated potential outcome Y(0) = 10000 - 100*x + noise (higher risk -> lower revenue)
    y0 = 10000.0 - 100.0 * x + np.random.normal(0, 500, n)
    # Treated potential outcome Y(1) = Y(0) + true_tau
    y1 = y0 + true_tau + np.random.normal(0, 500, n)

    # Observed outcome Y = W*Y(1) + (1-W)*Y(0)
    y_obs = w * y1 + (1 - w) * y0

    # Naive observational difference: E[Y | W=1] - E[Y | W=0]
    # This is severely biased downwards because treated accounts had higher baseline risk (lower Y0)!
    naive_diff = np.mean(y_obs[w == 1]) - np.mean(y_obs[w == 0])
    # Expect naive difference to underestimate true_tau by > $1000 due to confounding by indication
    assert naive_diff < true_tau - 1000.0

    # Execute Doubly Robust AIPW estimator
    # Linear outcome models
    from sklearn.linear_model import LinearRegression

    model_1 = LinearRegression().fit(x[w == 1].reshape(-1, 1), y_obs[w == 1])
    model_0 = LinearRegression().fit(x[w == 0].reshape(-1, 1), y_obs[w == 0])

    mu_1 = model_1.predict(x.reshape(-1, 1))
    mu_0 = model_0.predict(x.reshape(-1, 1))

    tau_aipw, std_err, ci_lower, ci_upper = store.compute_aipw_treatment_effect(
        outcomes=y_obs,
        treatments=w,
        propensities=e,
        mu_1_preds=mu_1,
        mu_0_preds=mu_0,
    )

    # AIPW must recover true_tau (+5000.0) within 95% confidence interval!
    assert ci_lower <= true_tau <= ci_upper
    assert abs(tau_aipw - true_tau) < 500.0  # Within $500 of true effect


def test_action_hub_integration_with_decision_outcomes_store():
    engine = HotStateEngine(db_path=":memory:")
    store = DecisionOutcomesStore(hot_state_engine=engine)
    hub = ActionIntentHub(outcomes_store=store, hot_state_engine=engine)

    token = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={"partner_ids": ["P-99"], "playbook_id": "VIP_RETENTION", "budget": 1500.0},
        evidence_refs=["CHURN-99"],
        propensity_score=0.76,
        causal_context={"partner_tier": 2, "churn_risk": 0.65},
    )

    # Check store has proposal record
    record = store.get_record_by_intent(token.intent_id)
    assert record is not None
    assert record.propensity_score == 0.76
    assert record.manager_override_flag is False

    # Approve with manager override
    hub.approve_action(
        token.intent_id,
        approver_id="MGR_ALICE",
        role="PARTNER_LEAD",
        comment="Adjusted retention playbook parameters",
        override_applied=True,
        override_reason="Partner agreed to 12-month exclusive lock",
    )

    updated_record = store.get_record_by_intent(token.intent_id)
    assert updated_record.manager_override_flag is True
    assert updated_record.override_reason == "Partner agreed to 12-month exclusive lock"
