"""Doubly Robust Augmented Inverse Probability Weighting (AIPW) and Propensity Logging (US5, FR-023, FR-024).

Implements:
1. compute_propensity_score: Sigmoid propensity calculation with strict [0.01, 0.99] positivity clipping.
2. AIPWEstimator: Semi-parametric doubly robust causal effect estimation combining logistic propensity
   modeling with regularized outcome regression.
"""

import numpy as np


def compute_propensity_score(
    covariates: dict[str, float],
    weights: dict[str, float] | None = None,
    bias: float = 0.0,
) -> float:
    """Compute logistic propensity score e(X) with strict positivity bounds [0.01, 0.99].

    Formula:
        z = bias + sum(w_k * x_k)
        e(X) = clip(1 / (1 + exp(-z)), 0.01, 0.99)
    """
    if weights is None:
        # Default unit weighting normalized across keys
        n = max(len(covariates), 1)
        weights = {k: 1.0 / n for k in covariates}

    z = bias
    for k, val in covariates.items():
        w = weights.get(k, 0.0)
        z += float(w) * float(val)

    # Sigmoid with numerical stability
    if z >= 35.0:
        score = 1.0
    elif z <= -35.0:
        score = 0.0
    else:
        score = 1.0 / (1.0 + float(np.exp(-z)))

    # Positivity clipping per Principle III & ADR-005
    clipped = float(np.clip(score, 0.01, 0.99))
    return round(clipped, 4)


from sklearn.linear_model import LogisticRegression, Ridge


class AIPWEstimator:
    """Doubly Robust Augmented Inverse Probability Weighting (AIPW) causal effect estimator."""

    def __init__(self, l2_reg: float = 1.0) -> None:
        self.l2_reg = l2_reg

    def fit_estimate(
        self,
        covariates: np.ndarray | list[list[float]],
        treatment: np.ndarray | list[int],
        outcomes: np.ndarray | list[float],
    ) -> float:
        """Fit doubly robust AIPW estimator on logged observational decisions.

        Formula:
            tau_hat = 1/N sum [ (mu_1(X) + A(Y - mu_1(X)) / e(X)) -
                                (mu_0(X) + (1-A)(Y - mu_0(X)) / (1 - e(X))) ]
        """
        x_raw = np.asarray(covariates, dtype=float)
        a = np.asarray(treatment, dtype=float)
        y = np.asarray(outcomes, dtype=float)

        n = len(a)
        if n == 0:
            return 0.0

        # 1. Fit Propensity Model e(X)
        # Handle case where all 'a' are the same
        if len(np.unique(a)) < 2:
            return 0.0
            
        C_val = 1.0 / self.l2_reg if self.l2_reg > 0 else 1e9
        prop_model = LogisticRegression(C=C_val, penalty='l2', max_iter=1000)
        prop_model.fit(x_raw, a)
        e_hat = prop_model.predict_proba(x_raw)[:, 1]
        
        # Positivity clipping [0.01, 0.99]
        e_hat = np.clip(e_hat, 0.01, 0.99)

        # 2. Fit Outcome Models mu_1(X) and mu_0(X)
        mask_1 = a == 1
        mask_0 = a == 0

        if np.sum(mask_1) < 2 or np.sum(mask_0) < 2:
            # Fall back to naive difference if insufficient treatment variation
            y1_mean = np.mean(y[mask_1]) if np.sum(mask_1) > 0 else 0.0
            y0_mean = np.mean(y[mask_0]) if np.sum(mask_0) > 0 else 0.0
            return float(y1_mean - y0_mean)

        model_y1 = Ridge(alpha=self.l2_reg)
        model_y1.fit(x_raw[mask_1], y[mask_1])
        model_y0 = Ridge(alpha=self.l2_reg)
        model_y0.fit(x_raw[mask_0], y[mask_0])

        mu_1 = model_y1.predict(x_raw)
        mu_0 = model_y0.predict(x_raw)

        # 3. Compute Doubly Robust Score for each observation
        gamma_1 = mu_1 + (a * (y - mu_1)) / e_hat
        gamma_0 = mu_0 + ((1.0 - a) * (y - mu_0)) / (1.0 - e_hat)

        tau_aipw = float(np.mean(gamma_1 - gamma_0))
        return tau_aipw

