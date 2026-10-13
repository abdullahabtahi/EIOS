"""Dual-Horizon Peer Cohort Baselines & Anomaly Scorer (US5 / P2).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/spec.md (User Story 5)
- .specify/memory/constitution.md (Principles I, VI)

Solves the cold-start problem by evaluating new accounts against peer cohorts,
smoothly transitioning to robust personalized baselines as account history matures.
"""

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CohortProfile:
    cohort_id: str
    median_deposit: float
    mad_deposit: float
    median_velocity_24h: float = 1.0


@dataclass(frozen=True)
class ClientBaseline:
    client_id: str
    median_deposit: float
    mad_deposit: float
    transaction_count: int


@dataclass(frozen=True)
class AnomalyScoreResult:
    client_id: str
    anomaly_score: float
    robust_z_score: float
    is_outlier: bool
    evaluation_mode: str
    details: dict[str, Any] = field(default_factory=dict)


class PeerBaselineEngine:
    """Computes cohort baselines and personal MAD deviations across customer lifecycles."""

    def __init__(self) -> None:
        self._cohorts: dict[str, CohortProfile] = {}
        self._clients: dict[str, ClientBaseline] = {}

    def register_cohort(
        self,
        cohort_id: str,
        median_deposit: float,
        mad_deposit: float,
        median_velocity_24h: float = 1.0,
    ) -> None:
        """Register or update a peer group cohort profile."""
        self._cohorts[cohort_id] = CohortProfile(
            cohort_id=cohort_id,
            median_deposit=max(1.0, median_deposit),
            mad_deposit=max(1.0, mad_deposit),
            median_velocity_24h=median_velocity_24h,
        )

    def register_client_personal_baseline(
        self,
        client_id: str,
        median_deposit: float,
        mad_deposit: float,
        transaction_count: int,
    ) -> None:
        """Register historical personal baseline for an established client."""
        self._clients[client_id] = ClientBaseline(
            client_id=client_id,
            median_deposit=max(1.0, median_deposit),
            mad_deposit=max(1.0, mad_deposit),
            transaction_count=transaction_count,
        )

    def _calc_robust_z(self, value: float, median: float, mad: float) -> float:
        """Calculate robust Z-score scaled by 1.4826 for normal consistency."""
        scale = max(1.0, 1.4826 * mad)
        return (value - median) / scale

    def _z_to_prob(self, z: float) -> float:
        """Map robust Z-score to an anomaly probability [0.0, 1.0]."""
        if z <= 0.0:
            return 0.05
        # Logistic curve centered around z = 2.5
        prob = 1.0 / (1.0 + math.exp(-(z - 2.5)))
        return float(np.clip(prob, 0.05, 0.99))

    def evaluate_client_anomaly(
        self,
        client_id: str,
        cohort_id: str,
        deposit_amount: float,
        transaction_count: int = 1,
        tenure_days: float = 1.0,
    ) -> AnomalyScoreResult:
        """Evaluate deposit anomaly across cold-start or mature personal horizon."""
        cohort = self._cohorts.get(
            cohort_id,
            CohortProfile(cohort_id="DEFAULT", median_deposit=300.0, mad_deposit=150.0),
        )

        cohort_z = self._calc_robust_z(deposit_amount, cohort.median_deposit, cohort.mad_deposit)
        cohort_prob = self._z_to_prob(cohort_z)

        # Transition factor alpha: 0.0 for cold-start (< 5 txns), 1.0 for mature (>= 20 txns)
        has_personal = client_id in self._clients
        if transaction_count < 5 or not has_personal:
            alpha = 0.0
            eval_mode = "COHORT_ONLY"
            final_prob = cohort_prob
            final_z = cohort_z
        else:
            personal = self._clients[client_id]
            alpha = min(1.0, max(0.0, float(transaction_count) / 20.0))
            eval_mode = "PERSONAL_DOMINANT" if alpha >= 0.8 else "BLENDED"

            personal_z = self._calc_robust_z(
                deposit_amount, personal.median_deposit, personal.mad_deposit
            )
            personal_prob = self._z_to_prob(personal_z)

            final_prob = alpha * personal_prob + (1.0 - alpha) * cohort_prob
            final_z = alpha * personal_z + (1.0 - alpha) * cohort_z

        is_outlier = final_prob >= 0.70 or final_z >= 3.5

        return AnomalyScoreResult(
            client_id=client_id,
            anomaly_score=round(final_prob, 4),
            robust_z_score=round(final_z, 2),
            is_outlier=is_outlier,
            evaluation_mode=eval_mode,
            details={
                "deposit_amount": deposit_amount,
                "cohort_id": cohort_id,
                "cohort_z": round(cohort_z, 2),
                "alpha_personal_weight": round(alpha, 2),
                "transaction_count": transaction_count,
            },
        )
