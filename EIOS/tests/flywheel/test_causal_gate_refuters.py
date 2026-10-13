"""Tests for User Story 2: Causal-Evidence Gate Refuter Suite (Principle III)."""

import numpy as np

from tests.flywheel.test_aipw_estimator import generate_confounded_dataset


def test_placebo_treatment_refuter():
    from eios.flywheel.refuters import CausalEvidenceGate, PlaceboRefuterResult

    Y, W, propensity, X, _ = generate_confounded_dataset(n_samples=500, true_tau=1500.0, seed=42)
    gate = CausalEvidenceGate()

    # Placebo test: random treatment assignment should eliminate estimated effect
    placebo_res = gate.run_placebo_refuter(Y=Y, W=W, propensity=propensity, X=X, seed=101)

    assert isinstance(placebo_res, PlaceboRefuterResult)
    assert placebo_res.passed is True
    # Placebo effect should be close to zero (< 25% of baseline tau or statistically insignificant)
    assert abs(placebo_res.placebo_effect) < 400.0


def test_random_common_cause_refuter():
    from eios.flywheel.refuters import CausalEvidenceGate, CommonCauseRefuterResult

    Y, W, propensity, X, _ = generate_confounded_dataset(n_samples=500, true_tau=1500.0, seed=42)
    gate = CausalEvidenceGate()

    # Adding an unobserved random noise covariate should not significantly alter effect
    rcc_res = gate.run_random_common_cause_refuter(Y=Y, W=W, propensity=propensity, X=X, seed=202)

    assert isinstance(rcc_res, CommonCauseRefuterResult)
    assert rcc_res.passed is True
    assert rcc_res.relative_change <= 0.10  # Must be within 10% change


def test_bootstrap_subset_refuter():
    from eios.flywheel.refuters import CausalEvidenceGate, SubsetRefuterResult

    Y, W, propensity, X, _ = generate_confounded_dataset(n_samples=500, true_tau=1500.0, seed=42)
    gate = CausalEvidenceGate()

    subset_res = gate.run_subset_refuter(
        Y=Y, W=W, propensity=propensity, X=X, subset_fraction=0.8, n_iterations=5, seed=303
    )

    assert isinstance(subset_res, SubsetRefuterResult)
    assert subset_res.passed is True
    assert subset_res.stability_pct >= 0.85  # High stability across subsets


def test_full_causal_evidence_gate_evaluation():
    from eios.flywheel.refuters import CausalEvidenceGate

    # Ground truth positive effect
    Y, W, propensity, X, _ = generate_confounded_dataset(n_samples=600, true_tau=2000.0, seed=777)
    gate = CausalEvidenceGate()

    gate_report = gate.evaluate_gate(
        Y=Y,
        W=W,
        propensity=propensity,
        X=X,
        target_metric="partner_retention_usd",
        intervention_type="commission_boost",
        seed=888,
    )

    assert gate_report.gate_passed is True
    assert gate_report.placebo_passed is True
    assert gate_report.common_cause_passed is True
    assert gate_report.subset_passed is True
    assert gate_report.ci_excludes_zero is True


def test_gate_rejects_spurious_effect():
    from eios.flywheel.refuters import CausalEvidenceGate

    # Generate pure noise outcome (true_tau = 0.0)
    rng = np.random.default_rng(999)
    n = 200
    X = rng.uniform(0, 1, size=(n, 1))
    propensity = np.full(n, 0.5)
    W = rng.binomial(1, 0.5, size=n).astype(np.float64)
    Y = rng.normal(100.0, 50.0, size=n)  # No relationship with W

    gate = CausalEvidenceGate()
    gate_report = gate.evaluate_gate(
        Y=Y,
        W=W,
        propensity=propensity,
        X=X,
        target_metric="spurious_metric",
        intervention_type="no_op",
        seed=111,
    )

    # Must fail because CI covers zero or effect is insignificant
    assert gate_report.gate_passed is False
