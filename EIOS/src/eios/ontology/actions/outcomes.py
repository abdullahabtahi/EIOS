"""Multi-Horizon Decision Outcomes Ledger and Doubly Robust AIPW Estimator (US5)."""

from datetime import UTC, datetime
import json
import threading
from typing import Any
import uuid

import numpy as np
from scipy import stats

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.models import DecisionOutcomeRecord


class DecisionOutcomesStore:
    """Captures proposal-time propensity scores e(X), causal covariates, and multi-horizon actuals."""

    def __init__(self, hot_state_engine: HotStateEngine | None = None) -> None:
        self.hot_state = hot_state_engine
        self._records: dict[str, DecisionOutcomeRecord] = {}
        self._intent_index: dict[str, str] = {}
        self._lock = threading.Lock()

    def record_decision(
        self,
        intent_id: str,
        entity_id: str,
        action_type: str,
        treatment_assigned: int,
        propensity_score: float,
        causal_features: dict[str, Any],
        manager_override_flag: bool = False,
        override_reason: str | None = None,
    ) -> DecisionOutcomeRecord:
        """Record decision-time covariates, propensity score, and manager overrides."""
        with self._lock:
            outcome_id = str(uuid.uuid4())
            now = datetime.now(UTC)

            # Ensure numeric float features
            cleaned_features = {
                k: float(v) if isinstance(v, (int, float)) else 0.0
                for k, v in causal_features.items()
            }

            record = DecisionOutcomeRecord(
                outcome_id=outcome_id,
                intent_id=intent_id,
                entity_id=entity_id,
                action_type=action_type,
                treatment_assigned=treatment_assigned,
                propensity_score=float(propensity_score),
                causal_features=cleaned_features,
                manager_override_flag=manager_override_flag,
                override_reason=override_reason,
                observed_retained_revenue_30d=None,
                observed_retained_revenue_60d=None,
                actual_churn_60d=None,
                clawback_recovered_usd_90d=None,
                recorded_at=now,
                reconciled_at=None,
            )

            self._records[outcome_id] = record
            self._intent_index[intent_id] = outcome_id

            if self.hot_state:
                self._persist_to_hot_state(record)

            return record

    def update_override(self, intent_id: str, override_reason: str | None = None) -> None:
        """Update manager override flag and reason for an existing intent record."""
        with self._lock:
            if intent_id in self._intent_index:
                outcome_id = self._intent_index[intent_id]
                rec = self._records[outcome_id]
                rec.manager_override_flag = True
                rec.override_reason = override_reason
                if self.hot_state:
                    self._persist_to_hot_state(rec)

    def reconcile_outcomes(
        self,
        outcome_id: str,
        observed_retained_revenue_30d: float | None = None,
        observed_retained_revenue_60d: float | None = None,
        actual_churn_60d: bool | None = None,
        clawback_recovered_usd_90d: float | None = None,
    ) -> DecisionOutcomeRecord:
        """Reconcile forward actuals at elapsed observation horizons."""
        with self._lock:
            if outcome_id not in self._records:
                raise KeyError(f"Outcome record '{outcome_id}' not found.")

            rec = self._records[outcome_id]
            rec.observed_retained_revenue_30d = observed_retained_revenue_30d
            rec.observed_retained_revenue_60d = observed_retained_revenue_60d
            rec.actual_churn_60d = actual_churn_60d
            rec.clawback_recovered_usd_90d = clawback_recovered_usd_90d
            rec.reconciled_at = datetime.now(UTC)

            if self.hot_state:
                self._persist_to_hot_state(rec)

            return rec

    def get_record_by_intent(self, intent_id: str) -> DecisionOutcomeRecord | None:
        with self._lock:
            if intent_id in self._intent_index:
                outcome_id = self._intent_index[intent_id]
                return self._records.get(outcome_id)
            return None

    def _persist_to_hot_state(self, rec: DecisionOutcomeRecord) -> None:
        """Persist record into DuckDB decision_outcomes_ledger."""
        cursor = self.hot_state.get_cursor()
        cursor.execute("DELETE FROM decision_outcomes_ledger WHERE outcome_id = ?", [rec.outcome_id])
        cursor.execute(
            """
            INSERT INTO decision_outcomes_ledger (
                outcome_id, intent_id, partner_id, playbook_id, treatment_assigned,
                propensity_score, observed_retained_revenue_60d, actual_churn_60d,
                recorded_at, manager_override_flag, override_reason, unobserved_signal_proxy,
                observed_retained_revenue_30d, clawback_recovered_usd_90d, reconciled_at,
                causal_features
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                rec.outcome_id,
                rec.intent_id,
                rec.entity_id,
                rec.action_type,
                rec.treatment_assigned,
                rec.propensity_score,
                rec.observed_retained_revenue_60d or 0.0,
                rec.actual_churn_60d if rec.actual_churn_60d is not None else False,
                rec.recorded_at,
                rec.manager_override_flag,
                rec.override_reason,
                0.0,
                rec.observed_retained_revenue_30d,
                rec.clawback_recovered_usd_90d,
                rec.reconciled_at,
                json.dumps(rec.causal_features),
            ],
        )

    def compute_aipw_treatment_effect(
        self,
        outcomes: np.ndarray,
        treatments: np.ndarray,
        propensities: np.ndarray,
        mu_1_preds: np.ndarray,
        mu_0_preds: np.ndarray,
        alpha: float = 0.05,
    ) -> tuple[float, float, float, float]:
        """Compute Doubly Robust Augmented Inverse Probability Weighting (AIPW) causal effect.

        Returns (tau_aipw, std_err, ci_lower, ci_upper).
        """
        w = np.asarray(treatments, dtype=float)
        y = np.asarray(outcomes, dtype=float)
        e = np.clip(np.asarray(propensities, dtype=float), 0.01, 0.99)
        mu_1 = np.asarray(mu_1_preds, dtype=float)
        mu_0 = np.asarray(mu_0_preds, dtype=float)

        # Doubly Robust score function Gamma_i
        gamma = (
            (mu_1 - mu_0)
            + (w * (y - mu_1) / e)
            - ((1.0 - w) * (y - mu_0) / (1.0 - e))
        )

        n = len(gamma)
        tau_aipw = float(np.mean(gamma))
        sample_var = float(np.var(gamma, ddof=1))
        std_err = float(np.sqrt(sample_var / n))

        z_crit = float(stats.norm.ppf(1.0 - alpha / 2.0))
        ci_lower = tau_aipw - z_crit * std_err
        ci_upper = tau_aipw + z_crit * std_err

        return tau_aipw, std_err, ci_lower, ci_upper
