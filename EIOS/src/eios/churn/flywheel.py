"""Doubly Robust AIPW Causal Estimator and Closed-Loop Flywheel (T029, T030 / US5).

Performs:
1. Augmented Inverse Propensity Weighting (AIPW) to estimate Average Treatment Effect (ATE)
   unbiased by confounding-by-indication (Principle I & research.md §4).
2. Playbook weight recalibration based on observed forward outcomes in decision_outcomes_ledger.
"""

import logging
from datetime import date
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import scipy.stats as stats
from sklearn.linear_model import LinearRegression

from eios.churn.models import DecisionOutcomeRecord
from eios.ingestion.hot_state import HotStateEngine

logger = logging.getLogger("eios.churn.flywheel")


class AIPWCausalEstimator:
    """Doubly Robust Augmented Inverse Propensity Weighting (AIPW) Causal Estimator."""

    def __init__(self, clip_bounds: tuple[float, float] = (0.01, 0.99)) -> None:
        self.clip_min, self.clip_max = clip_bounds

    def estimate_ate(
        self,
        df: pd.DataFrame,
        feature_cols: list[str] | None = None,
    ) -> dict[str, Any]:
        """Calculates Average Treatment Effect (ATE) using Doubly Robust AIPW.

        Formula:
            tau_i = mu_1(X_i) - mu_0(X_i) + [W_i * (Y_i - mu_1(X_i)) / e(X_i)] - [(1 - W_i) * (Y_i - mu_0(X_i)) / (1 - e(X_i))]
            ATE = (1/N) * sum(tau_i)
        """
        if df.empty or len(df) < 4:
            return {
                "ate": 0.0,
                "se": 0.0,
                "ci_lower": 0.0,
                "ci_upper": 0.0,
                "p_value": 1.0,
                "is_significant": False,
                "sample_size": len(df),
            }

        W = df["treatment_assigned"].values.astype(float)
        Y = df["observed_retained_revenue_60d"].values.astype(float)
        e = np.clip(df["propensity_score"].values.astype(float), self.clip_min, self.clip_max)

        n = len(df)

        # Build covariate matrix X
        if feature_cols and all(col in df.columns for col in feature_cols):
            X = df[feature_cols].values
        else:
            # Check for manager override and unobserved proxy features to mitigate confounding
            confounder_cols = [
                c for c in ["manager_override_flag", "unobserved_signal_proxy"] if c in df.columns
            ]
            if confounder_cols:
                extra_covs = df[confounder_cols].values.astype(float)
                X = np.hstack([e.reshape(-1, 1), extra_covs])
            else:
                # Use propensity score as 1D covariate feature
                X = e.reshape(-1, 1)

        treated_idx = W == 1
        control_idx = W == 0

        # Outcome regression models mu_1 and mu_0
        if np.sum(treated_idx) >= 2 and np.sum(control_idx) >= 2:
            reg_1 = LinearRegression().fit(X[treated_idx], Y[treated_idx])
            reg_0 = LinearRegression().fit(X[control_idx], Y[control_idx])
            mu_1 = reg_1.predict(X)
            mu_0 = reg_0.predict(X)
        else:
            # Fallback to group means if sample too small
            mu_1 = np.full(n, np.mean(Y[treated_idx]) if np.any(treated_idx) else np.mean(Y))
            mu_0 = np.full(n, np.mean(Y[control_idx]) if np.any(control_idx) else np.mean(Y))

        # AIPW individual treatment effect scores tau_i
        tau_i = mu_1 - mu_0 + (W * (Y - mu_1) / e) - ((1.0 - W) * (Y - mu_0) / (1.0 - e))

        ate = float(np.mean(tau_i))
        se = float(np.std(tau_i, ddof=1) / np.sqrt(n)) if n > 1 else 0.0

        ci_lower = ate - 1.96 * se
        ci_upper = ate + 1.96 * se

        if se > 1e-9:
            z_score = abs(ate / se)
            p_value = float(2 * (1 - stats.norm.cdf(z_score)))
        else:
            p_value = 1.0

        return {
            "ate": round(ate, 2),
            "se": round(se, 2),
            "ci_lower": round(ci_lower, 2),
            "ci_upper": round(ci_upper, 2),
            "p_value": round(p_value, 6),
            "is_significant": bool(p_value < 0.05),
            "sample_size": n,
        }


class PlaybookRecalibrator:
    """Manages the closed-loop flywheel by updating retention playbook weights based on causal ATE."""

    def __init__(self, hot_state: HotStateEngine | duckdb.DuckDBPyConnection) -> None:
        if isinstance(hot_state, HotStateEngine):
            self.conn = hot_state.get_cursor()
            self.hot_state = hot_state
        else:
            self.conn = hot_state
            self.hot_state = None
        self.estimator = AIPWCausalEstimator()

    def _get_cursor(self) -> duckdb.DuckDBPyConnection:
        if self.hot_state is not None:
            return self.hot_state.get_cursor()
        return self.conn

    def record_outcome(self, outcome: DecisionOutcomeRecord) -> None:
        """Persist an observed forward outcome record to decision_outcomes_ledger."""
        cursor = self._get_cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO decision_outcomes_ledger (
                outcome_id, intent_id, partner_id, playbook_id, treatment_assigned,
                propensity_score, observed_retained_revenue_60d, actual_churn_60d,
                recorded_at, manager_override_flag, override_reason, unobserved_signal_proxy
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """,
            (
                outcome.outcome_id,
                outcome.intent_id,
                outcome.partner_id,
                outcome.playbook_id,
                outcome.treatment_assigned,
                outcome.propensity_score,
                outcome.observed_retained_revenue_60d,
                outcome.actual_churn_60d,
                outcome.recorded_at,
                getattr(outcome, "manager_override_flag", False),
                getattr(outcome, "override_reason", None),
                getattr(outcome, "unobserved_signal_proxy", 0.0),
            ),
        )

    def recalibrate_playbook_weights(
        self,
        as_of_date: date | None = None,
        temperature: float = 2000.0,
    ) -> dict[str, float]:
        """Compute Doubly Robust ATE for each playbook and derive updated selection probabilities."""
        cursor = self._get_cursor()
        rows = cursor.execute("""
            SELECT
                playbook_id,
                treatment_assigned,
                propensity_score,
                observed_retained_revenue_60d,
                manager_override_flag,
                unobserved_signal_proxy
            FROM decision_outcomes_ledger
        """).fetchall()

        if not rows:
            logger.info("No decision outcome records found in ledger.")
            return {}

        df_all = pd.DataFrame(
            rows,
            columns=[
                "playbook_id",
                "treatment_assigned",
                "propensity_score",
                "observed_retained_revenue_60d",
                "manager_override_flag",
                "unobserved_signal_proxy",
            ],
        )

        ates: dict[str, float] = {}
        for pb_id, sub_df in df_all.groupby("playbook_id"):
            res = self.estimator.estimate_ate(sub_df)
            ates[str(pb_id)] = res["ate"]

        # Softmax weight conversion
        pb_ids = list(ates.keys())
        ate_vals = np.array([ates[pid] for pid in pb_ids], dtype=float)

        # Scale by temperature and prevent exponent overflow
        z = np.clip(ate_vals / max(temperature, 1.0), -20.0, 20.0)
        exp_z = np.exp(z - np.max(z))
        weights = exp_z / np.sum(exp_z)

        return {pid: round(float(w), 4) for pid, w in zip(pb_ids, weights)}  # noqa: B905
