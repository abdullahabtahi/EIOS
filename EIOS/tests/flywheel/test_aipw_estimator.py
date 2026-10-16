"""Tests for User Story 2: Doubly Robust AIPW Causal Uplift Estimator."""

import numpy as np
import pytest

from eios.flywheel.schemas import validate_contract


def generate_confounded_dataset(n_samples: int = 500, true_tau: float = 1200.0, seed: int = 42):
    """Generates synthetic confounded observational data simulating confounding by indication.

    Higher risk score X leads to higher treatment probability e(X) AND worse baseline outcome.
    Naive difference-in-means will severely underestimate the true positive treatment effect.
    """
    rng = np.random.default_rng(seed)

    # Covariate X: risk score ~ Uniform(0, 1)
    X = rng.uniform(0.0, 1.0, size=(n_samples, 1))

    # Propensity: operators approve treatment more often for high-risk accounts
    # e(X) ranges from ~0.2 to ~0.8
    propensity = 0.2 + 0.6 * X[:, 0]
    W = rng.binomial(1, propensity).astype(np.float64)

    # Potential outcomes:
    # Baseline outcome Y0 is negatively impacted by risk X: Y0 = 10000 - 4000 * X
    # Treatment adds true_tau: Y1 = Y0 + true_tau
    # Realized outcome: Y = Y0 + W * true_tau + noise
    noise = rng.normal(0, 100.0, size=n_samples)
    Y0 = 10000.0 - 4000.0 * X[:, 0]
    Y = Y0 + W * true_tau + noise

    return Y, W, propensity, X, true_tau


def test_aipw_bias_reduction_over_naive():
    from eios.flywheel.aipw import AIPWCausalEstimator

    Y, W, propensity, X, true_tau = generate_confounded_dataset(
        n_samples=1000, true_tau=1500.0, seed=123
    )

    # Naive difference in means
    treated_mean = np.mean(Y[W == 1])
    control_mean = np.mean(Y[W == 0])
    naive_ate = treated_mean - control_mean
    naive_bias = abs(naive_ate - true_tau)

    # AIPW estimation
    estimator = AIPWCausalEstimator()
    estimate = estimator.estimate(
        Y=Y,
        W=W,
        propensity=propensity,
        X=X,
        target_metric="revenue_retained_60d",
        intervention_type="fee_tier_restructure",
    )

    aipw_bias = abs(estimate.ate_aipw - true_tau)

    # AIPW must achieve >= 80% bias reduction compared to naive difference-in-means
    bias_reduction = (naive_bias - aipw_bias) / naive_bias
    assert bias_reduction >= 0.80, f"Bias reduction {bias_reduction:.2%} is below 80% threshold"

    # CI should cover the true effect
    assert estimate.ci_lower <= true_tau <= estimate.ci_upper
    assert estimate.is_significant is True
    assert estimate.standard_error > 0.0


def test_aipw_contract_validation():
    from eios.flywheel.aipw import AIPWCausalEstimator

    Y, W, propensity, X, _ = generate_confounded_dataset(n_samples=200, seed=99)
    estimator = AIPWCausalEstimator()
    estimate = estimator.estimate(
        Y=Y,
        W=W,
        propensity=propensity,
        X=X,
        target_metric="retained_revenue_60d",
        intervention_type="step_up_kyc",
    )

    dumped = estimate.model_dump(mode="json")
    assert validate_contract(dumped, "causal-uplift-estimate") is True


def test_aipw_small_sample_bounds():
    from eios.flywheel.aipw import AIPWCausalEstimator

    estimator = AIPWCausalEstimator()
    with pytest.raises(ValueError, match="at least 4 samples"):
        estimator.estimate(
            Y=np.array([1.0, 2.0]),
            W=np.array([1.0, 0.0]),
            propensity=np.array([0.5, 0.5]),
            X=np.array([[1.0], [1.0]]),
            target_metric="revenue",
            intervention_type="test",
        )


def test_fit_outcome_models_indicator_indexing():
    """Verify fit_outcome_models indexes treated and control units correctly with float indicators."""
    from eios.flywheel.aipw import AIPWCausalEstimator

    estimator = AIPWCausalEstimator()
    Y = np.array([10.0, 20.0, 30.0, 40.0])
    W = np.array([1.0, 0.0, 1.0, 0.0])
    X = np.array([[1.0], [2.0], [3.0], [4.0]])

    mu_1, mu_0 = estimator.fit_outcome_models(Y, W, X)
    assert len(mu_1) == 4
    assert len(mu_0) == 4
