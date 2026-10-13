"""Tests for AIPW confounder mitigation and manager override adjustment (FM-2 Countermeasure)."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from eios.churn.flywheel import AIPWCausalEstimator, PlaybookRecalibrator
from eios.churn.models import DecisionOutcomeRecord
from eios.ingestion.hot_state import HotStateEngine


def test_aipw_estimator_handles_manager_override_covariates():
    estimator = AIPWCausalEstimator()

    # Generate synthetic dataset where manager overrides create confounding
    np.random.seed(42)
    n = 100
    override = np.random.binomial(1, 0.3, n)
    proxy = np.random.normal(0, 1, n)
    # Propensity depends on override
    propensity = 1.0 / (1.0 + np.exp(-(0.5 + 1.2 * override + 0.8 * proxy)))
    propensity = np.clip(propensity, 0.05, 0.95)
    treatment = np.random.binomial(1, propensity, n)
    # True treatment effect is 2500.0, plus confounding from override
    revenue = (
        8000.0 + 2500.0 * treatment + 3000.0 * override + 500.0 * proxy + np.random.normal(0, 50, n)
    )

    df = pd.DataFrame(
        {
            "treatment_assigned": treatment,
            "observed_retained_revenue_60d": revenue,
            "propensity_score": propensity,
            "manager_override_flag": override,
            "unobserved_signal_proxy": proxy,
        }
    )

    res = estimator.estimate_ate(df)
    assert res["sample_size"] == n
    # Estimated ATE should be near true ATE of 2500
    assert 2200.0 <= res["ate"] <= 2800.0
    assert res["is_significant"] is True


def test_playbook_recalibrator_persists_override_fields():
    engine = HotStateEngine(":memory:")
    recalibrator = PlaybookRecalibrator(engine)

    record = DecisionOutcomeRecord(
        outcome_id="OUT-MGR-1",
        intent_id="INT-1",
        partner_id="P-101",
        playbook_id="VIP_Custom_Retention",
        treatment_assigned=1,
        propensity_score=0.85,
        observed_retained_revenue_60d=15000.0,
        actual_churn_60d=False,
        recorded_at=datetime.now(UTC),
        manager_override_flag=True,
        override_reason="Strategic VIP executive request",
        unobserved_signal_proxy=0.92,
    )

    recalibrator.record_outcome(record)

    cursor = engine.get_cursor()
    row = cursor.execute("""
        SELECT outcome_id, manager_override_flag, override_reason, unobserved_signal_proxy
        FROM decision_outcomes_ledger WHERE outcome_id = 'OUT-MGR-1'
    """).fetchone()

    assert row[0] == "OUT-MGR-1"
    assert row[1] is True
    assert row[2] == "Strategic VIP executive request"
    assert abs(row[3] - 0.92) < 1e-4

    engine.close()
