"""Doubly Robust Augmented Inverse Propensity Weighting (AIPW) Causal Estimator."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import numpy as np
from scipy import stats
from sklearn.linear_model import Ridge

from eios.flywheel.covariates import clip_propensity_scores
from eios.flywheel.models import CausalUpliftEstimate


class AIPWCausalEstimator:
    """Doubly Robust AIPW counterfactual causal estimator.

    Corrects for confounding by indication by simultaneously modeling:
    1. Treatment assignment mechanism e(X) (logged at proposal time)
    2. Outcome surface regressions mu_1(X) and mu_0(X)

    Satisfies the double-robustness property: if EITHER the propensity model
    OR the outcome models are correctly specified, the treatment effect
    estimate tau_AIPW remains asymptotically unbiased.
    """

    def __init__(self, alpha_ridge: float = 1.0, epsilon: float = 0.01) -> None:
        self.alpha_ridge = alpha_ridge
        self.epsilon = epsilon

    def fit_outcome_models(
        self,
        Y: np.ndarray,
        W: np.ndarray,
        X: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Fits outcome models mu_1(X) on treated units and mu_0(X) on control units."""
        n_samples = len(Y)
        treated_idx = np.nonzero(np.isclose(W, 1.0))[0]
        control_idx = np.nonzero(np.isclose(W, 0.0))[0]

        if len(treated_idx) == 0 or len(control_idx) == 0:
            raise ValueError("Both treated and control units are required for AIPW estimation")

        # Fit treated outcome model mu_1
        if len(treated_idx) > X.shape[1]:
            model_1 = Ridge(alpha=self.alpha_ridge).fit(X[treated_idx], Y[treated_idx])
            mu_1 = model_1.predict(X)
        else:
            mu_1 = np.full(n_samples, float(np.mean(Y[treated_idx])))

        # Fit control outcome model mu_0
        if len(control_idx) > X.shape[1]:
            model_0 = Ridge(alpha=self.alpha_ridge).fit(X[control_idx], Y[control_idx])
            mu_0 = model_0.predict(X)
        else:
            mu_0 = np.full(n_samples, float(np.mean(Y[control_idx])))

        return mu_1, mu_0

    def compute_influence_function(
        self,
        Y: np.ndarray,
        W: np.ndarray,
        propensity: np.ndarray,
        mu_1: np.ndarray,
        mu_0: np.ndarray,
    ) -> np.ndarray:
        """Computes per-observation uncentered influence function values psi_i."""
        e = clip_propensity_scores(propensity, epsilon=self.epsilon)
        psi = (mu_1 - mu_0) + (W * (Y - mu_1) / e) - ((1.0 - W) * (Y - mu_0) / (1.0 - e))
        return psi

    def estimate(  # noqa: PLR0913
        self,
        Y: np.ndarray,
        W: np.ndarray,
        propensity: np.ndarray,
        X: np.ndarray,
        target_metric: str,
        intervention_type: str,
        placebo_effect: float = 0.0,
        refuter_stability_pct: float = 100.0,
        causal_gate_passed: bool | None = None,
    ) -> CausalUpliftEstimate:
        """Computes Doubly Robust AIPW Average Treatment Effect and confidence bounds."""
        Y = np.asarray(Y, dtype=np.float64)
        W = np.asarray(W, dtype=np.float64)
        propensity = np.asarray(propensity, dtype=np.float64)
        X = np.asarray(X, dtype=np.float64)

        n = len(Y)
        if n < 4:
            raise ValueError(f"Estimation requires at least 4 samples, got {n}")

        treatment_count = int(np.sum(np.isclose(W, 1.0, atol=1e-9)))
        control_count = int(np.sum(np.isclose(W, 0.0, atol=1e-9)))
        if treatment_count < 1 or control_count < 1:
            raise ValueError(
                f"Both treated (got {treatment_count}) and control (got {control_count}) units required"
            )

        mu_1, mu_0 = self.fit_outcome_models(Y=Y, W=W, X=X)
        psi = self.compute_influence_function(Y=Y, W=W, propensity=propensity, mu_1=mu_1, mu_0=mu_0)

        ate = float(np.mean(psi))
        # Asymptotic influence-function standard error
        variance = float(np.var(psi, ddof=1) / n)
        se = float(np.sqrt(max(variance, 1e-12)))

        ci_lower = round(ate - 1.959964 * se, 4)
        ci_upper = round(ate + 1.959964 * se, 4)

        # Two-sided p-value against null hypothesis tau = 0
        z_stat = abs(ate) / se if se > 0 else 0.0
        p_val = float(2.0 * (1.0 - stats.norm.cdf(z_stat)))
        p_val = max(0.0, min(1.0, round(p_val, 6)))
        is_significant = p_val < 0.05

        if causal_gate_passed is None:
            # Standard gate criteria: significant and CI strictly excludes zero
            excludes_zero = (ci_lower > 0.0) or (ci_upper < 0.0)
            causal_gate_passed = is_significant and excludes_zero

        return CausalUpliftEstimate(
            estimate_id=str(uuid.uuid4()),
            target_metric=target_metric,
            intervention_type=intervention_type,
            sample_size=n,
            treatment_count=treatment_count,
            control_count=control_count,
            ate_aipw=round(ate, 4),
            standard_error=round(se, 4),
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_val,
            is_significant=is_significant,
            causal_gate_passed=causal_gate_passed,
            placebo_effect=round(placebo_effect, 4),
            refuter_stability_pct=round(refuter_stability_pct, 2),
            evaluated_at=datetime.now(UTC),
        )
