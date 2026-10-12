"""Tests for Doubly Robust AIPW Causal Flywheel and Propensity Logging (T028, US5)."""

import numpy as np

from eios.synthesis.aipw import AIPWEstimator, compute_propensity_score
from eios.synthesis.models import AIPWPropensityRecord


def test_propensity_score_calculation_and_clipping():
    """Verify propensity score calculation uses sigmoid and enforces strict [0.01, 0.99] bounds."""
    # Extreme positive covariates
    extreme_pos = {"x1": 100.0, "x2": 50.0}
    weights = {"x1": 2.0, "x2": 1.0}
    score_high = compute_propensity_score(extreme_pos, weights)
    assert score_high == 0.99

    # Extreme negative covariates
    extreme_neg = {"x1": -100.0, "x2": -50.0}
    score_low = compute_propensity_score(extreme_neg, weights)
    assert score_low == 0.01

    # Balanced covariates
    balanced = {"x1": 0.0, "x2": 0.0}
    score_mid = compute_propensity_score(balanced, weights)
    assert abs(score_mid - 0.50) < 1e-4


def test_aipw_doubly_robust_bias_reduction():
    """Verify AIPW estimator achieves >= 50% lower bias than naive observational differences."""
    rng = np.random.default_rng(seed=42)
    n = 1500
    true_ate = 15.0

    # Confounder X
    x = rng.normal(0.0, 1.0, size=n)

    # Treatment assignment confounded by X
    # Individuals with high X are much more likely to receive treatment
    logit_p = 1.6 * x
    true_propensity = 1.0 / (1.0 + np.exp(-logit_p))
    treatment = (rng.uniform(0.0, 1.0, size=n) < true_propensity).astype(int)

    # Potential outcomes: strongly dependent on X
    # Y(0) = 25.0 * X + noise
    # Y(1) = Y(0) + true_ate
    noise = rng.normal(0.0, 1.0, size=n)
    y0 = 25.0 * x + noise
    y1 = y0 + true_ate
    observed_y = treatment * y1 + (1 - treatment) * y0

    # Naive observational difference: E[Y | A=1] - E[Y | A=0]
    naive_diff = float(np.mean(observed_y[treatment == 1]) - np.mean(observed_y[treatment == 0]))
    naive_bias = abs(naive_diff - true_ate)

    # AIPW estimation
    covariates_matrix = x.reshape(-1, 1)
    estimator = AIPWEstimator()
    ate_hat = estimator.fit_estimate(
        covariates=covariates_matrix,
        treatment=treatment,
        outcomes=observed_y,
    )
    aipw_bias = abs(ate_hat - true_ate)

    # Assert >= 50% bias reduction against naive average
    assert aipw_bias <= 0.50 * naive_bias, (
        f"AIPW bias {aipw_bias:.4f} not <= 50% of naive bias {naive_bias:.4f} "
        f"(True ATE: {true_ate}, Naive: {naive_diff:.4f}, AIPW: {ate_hat:.4f})"
    )


def test_aipw_propensity_record_model():
    """Verify AIPWPropensityRecord model validation and constraints."""
    rec = AIPWPropensityRecord(
        intent_id="INT-991",
        action_type="AdjustPartnerTier",
        target_entity_id="P-101",
        propensity_score=0.72,
        covariates={"partner_churn_rate": 0.15, "tenure_months": 36.0},
        action_taken=1,
    )
    assert rec.propensity_score == 0.72
    assert rec.action_taken == 1
    assert rec.covariates["partner_churn_rate"] == 0.15
