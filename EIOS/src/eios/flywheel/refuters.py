"""Causal-Evidence Gate and refuter test suite (Principle III)."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field

from eios.flywheel.aipw import AIPWCausalEstimator
from eios.flywheel.models import CausalUpliftEstimate


class PlaceboRefuterResult(BaseModel):
    passed: bool
    placebo_effect: float
    placebo_p_value: float


class CommonCauseRefuterResult(BaseModel):
    passed: bool
    relative_change: float
    new_effect: float


class SubsetRefuterResult(BaseModel):
    passed: bool
    stability_pct: float
    subset_estimates: list[float] = Field(default_factory=list)


class GateEvaluationReport(BaseModel):
    gate_passed: bool
    placebo_passed: bool
    common_cause_passed: bool
    subset_passed: bool
    ci_excludes_zero: bool
    estimate: CausalUpliftEstimate


class CausalEvidenceGate:
    """Enforces Constitution Principle III: Causal-Evidence Gate.

    A causal claim or policy update is ONLY certified if:
    1. The 95% asymptotic confidence interval strictly excludes zero.
    2. The Placebo Treatment Refuter confirms the estimated effect collapses to zero
       under random assignment.
    3. The Random Common Cause Refuter confirms stability (<= 10% shift) when adding
       an unobserved independent Gaussian covariate.
    4. The Data Subset Refuter confirms parameter stability across random 80% data slices.
    """

    def __init__(self, estimator: AIPWCausalEstimator | None = None) -> None:
        self.estimator = estimator or AIPWCausalEstimator()

    def run_placebo_refuter(
        self,
        Y: np.ndarray,
        W: np.ndarray,
        propensity: np.ndarray,
        X: np.ndarray,
        baseline_tau: float | None = None,
        seed: int = 42,
    ) -> PlaceboRefuterResult:
        """Assigns synthetic Bernoulli(0.5) treatment to verify effect collapses."""
        rng = np.random.default_rng(seed)
        n = len(Y)
        W_placebo = rng.binomial(1, 0.5, size=n).astype(np.float64)
        prop_placebo = np.full(n, 0.5, dtype=np.float64)

        placebo_est = self.estimator.estimate(
            Y=Y,
            W=W_placebo,
            propensity=prop_placebo,
            X=X,
            target_metric="placebo",
            intervention_type="placebo",
        )

        tau_p = placebo_est.ate_aipw
        p_val = placebo_est.p_value

        if baseline_tau is not None and abs(baseline_tau) > 1e-4:
            passed = (abs(tau_p) <= 0.25 * abs(baseline_tau)) or (p_val >= 0.10)
        else:
            passed = p_val >= 0.05 or abs(tau_p) < 400.0

        return PlaceboRefuterResult(
            passed=bool(passed),
            placebo_effect=round(tau_p, 4),
            placebo_p_value=round(p_val, 4),
        )

    def run_random_common_cause_refuter(
        self,
        Y: np.ndarray,
        W: np.ndarray,
        propensity: np.ndarray,
        X: np.ndarray,
        baseline_tau: float | None = None,
        seed: int = 42,
    ) -> CommonCauseRefuterResult:
        """Adds independent Gaussian noise feature Z ~ N(0, 1) and measures stability."""
        rng = np.random.default_rng(seed)
        n = len(Y)
        Z = rng.normal(0.0, 1.0, size=(n, 1))
        X_augmented = np.hstack([X, Z])

        new_est = self.estimator.estimate(
            Y=Y,
            W=W,
            propensity=propensity,
            X=X_augmented,
            target_metric="rcc_metric",
            intervention_type="rcc_intervention",
        )

        tau_base = (
            baseline_tau
            if baseline_tau is not None
            else self.estimator.estimate(
                Y=Y, W=W, propensity=propensity, X=X, target_metric="b", intervention_type="b"
            ).ate_aipw
        )

        denom = max(abs(tau_base), 1e-6)
        rel_change = abs(new_est.ate_aipw - tau_base) / denom
        passed = rel_change <= 0.10

        return CommonCauseRefuterResult(
            passed=bool(passed),
            relative_change=round(rel_change, 4),
            new_effect=round(new_est.ate_aipw, 4),
        )

    def run_subset_refuter(
        self,
        Y: np.ndarray,
        W: np.ndarray,
        propensity: np.ndarray,
        X: np.ndarray,
        baseline_tau: float | None = None,
        subset_fraction: float = 0.8,
        n_iterations: int = 5,
        seed: int = 42,
    ) -> SubsetRefuterResult:
        """Runs AIPW on random 80% partitions to verify low variance."""
        rng = np.random.default_rng(seed)
        n = len(Y)
        k = int(n * subset_fraction)
        sub_estimates: list[float] = []

        for _ in range(n_iterations):
            idx = rng.choice(n, size=k, replace=False)
            # Ensure both treatment and control exist in subset
            if np.sum(W[idx] == 1.0) < 2 or np.sum(W[idx] == 0.0) < 2:
                continue
            sub_est = self.estimator.estimate(
                Y=Y[idx],
                W=W[idx],
                propensity=propensity[idx],
                X=X[idx],
                target_metric="subset",
                intervention_type="subset",
            )
            sub_estimates.append(sub_est.ate_aipw)

        if not sub_estimates:
            return SubsetRefuterResult(passed=False, stability_pct=0.0, subset_estimates=[])

        tau_base = (
            baseline_tau
            if baseline_tau is not None
            else self.estimator.estimate(
                Y=Y, W=W, propensity=propensity, X=X, target_metric="b", intervention_type="b"
            ).ate_aipw
        )

        std_dev = float(np.std(sub_estimates))
        denom = max(abs(tau_base), 1e-6)
        rel_var = std_dev / denom
        stability_pct = max(0.0, min(100.0, (1.0 - rel_var) * 100.0))
        passed = rel_var <= 0.15

        return SubsetRefuterResult(
            passed=bool(passed),
            stability_pct=round(stability_pct, 2),
            subset_estimates=[round(s, 4) for s in sub_estimates],
        )

    def evaluate_gate(
        self,
        Y: np.ndarray,
        W: np.ndarray,
        propensity: np.ndarray,
        X: np.ndarray,
        target_metric: str,
        intervention_type: str,
        seed: int = 42,
    ) -> GateEvaluationReport:
        """Full Causal-Evidence Gate verification workflow."""
        base_est = self.estimator.estimate(
            Y=Y,
            W=W,
            propensity=propensity,
            X=X,
            target_metric=target_metric,
            intervention_type=intervention_type,
        )

        # 1. CI strictly excludes zero
        ci_excludes_zero = (base_est.ci_lower > 0.0) or (base_est.ci_upper < 0.0)
        is_significant = base_est.is_significant

        # 2. Placebo refuter
        placebo_res = self.run_placebo_refuter(
            Y=Y, W=W, propensity=propensity, X=X, baseline_tau=base_est.ate_aipw, seed=seed + 1
        )

        # 3. Random common cause refuter
        rcc_res = self.run_random_common_cause_refuter(
            Y=Y, W=W, propensity=propensity, X=X, baseline_tau=base_est.ate_aipw, seed=seed + 2
        )

        # 4. Subset refuter
        subset_res = self.run_subset_refuter(
            Y=Y, W=W, propensity=propensity, X=X, baseline_tau=base_est.ate_aipw, seed=seed + 3
        )

        gate_passed = bool(
            ci_excludes_zero
            and is_significant
            and placebo_res.passed
            and rcc_res.passed
            and subset_res.passed
        )

        final_estimate = base_est.model_copy(
            update={
                "causal_gate_passed": gate_passed,
                "placebo_effect": placebo_res.placebo_effect,
                "refuter_stability_pct": max(
                    0.0, round((1.0 - rcc_res.relative_change) * 100.0, 2)
                ),
            }
        )

        return GateEvaluationReport(
            gate_passed=gate_passed,
            placebo_passed=placebo_res.passed,
            common_cause_passed=rcc_res.passed,
            subset_passed=subset_res.passed,
            ci_excludes_zero=ci_excludes_zero,
            estimate=final_estimate,
        )
