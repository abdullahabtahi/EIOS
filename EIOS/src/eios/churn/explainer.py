"""Deterministic signal contribution explainer across 5 signal families (T016 / Principle I & V).

Decomposes partner disengagement into deterministic signal contributions
anchored to canonical Layer 1 Data Products:
- DP6: partner_360
- DP8: commission_ledger
- DP9: partner_engagement_signals
- DP10: partner_comms
"""

from collections.abc import Sequence
from typing import Any

from eios.churn.models import SignalContribution, SignalFamily


class ChurnSignalExplainer:
    """Computes transparent feature contributions and identifies primary disengagement drivers."""

    def __init__(self) -> None:
        self.weights: dict[SignalFamily, float] = {
            SignalFamily.BEHAVIORAL: 1.8,
            SignalFamily.COMMUNICATION: 1.4,
            SignalFamily.RELATIONSHIP: -0.8,
            SignalFamily.FINANCIAL: 1.5,
            SignalFamily.COMPETITIVE: 2.2,
        }

    def compute_contributions(self, row: Any) -> list[SignalContribution]:
        """Calculates deterministic signal contributions for all 5 families from partner telemetry."""
        contributions: list[SignalContribution] = []

        # 1. Behavioral
        logins_recent = float(getattr(row, "logins_recent", 0))
        logins_prior = float(getattr(row, "logins_prior", 0))
        decay_delta = float(getattr(row, "login_velocity_decay_3w", 0.0))
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.BEHAVIORAL,
                metric_name="login_velocity_decay_3w",
                observed_value=logins_recent,
                baseline_value=logins_prior,
                relative_delta=round(decay_delta, 4),
                hazard_weight=self.weights[SignalFamily.BEHAVIORAL],
                citation_ref="DP9:partner_engagement_signals",
            )
        )

        # 2. Communication
        neg_tickets = float(getattr(row, "negative_tickets", 0))
        neg_ratio = float(getattr(row, "sentiment_negative_ratio", 0.0))
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.COMMUNICATION,
                metric_name="sentiment_negative_ratio",
                observed_value=neg_tickets,
                baseline_value=0.0,
                relative_delta=round(neg_ratio, 4),
                hazard_weight=self.weights[SignalFamily.COMMUNICATION],
                citation_ref="DP10:partner_comms",
            )
        )

        # 3. Relationship
        tenure = float(getattr(row, "tenure_months", 0))
        tenure_log = float(getattr(row, "tenure_months_log", 0.0))
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.RELATIONSHIP,
                metric_name="tenure_months",
                observed_value=tenure,
                baseline_value=12.0,
                relative_delta=round(tenure_log, 4),
                hazard_weight=self.weights[SignalFamily.RELATIONSHIP],
                citation_ref="DP6:partner_360",
            )
        )

        # 4. Financial
        comm_recent = float(getattr(row, "comm_recent", 0.0))
        comm_prior = float(getattr(row, "comm_prior", 0.0))
        comm_velocity = float(getattr(row, "commission_velocity_30d", 0.0))
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.FINANCIAL,
                metric_name="commission_velocity_30d",
                observed_value=comm_recent,
                baseline_value=comm_prior,
                relative_delta=round(comm_velocity, 4),
                hazard_weight=self.weights[SignalFamily.FINANCIAL],
                citation_ref="DP8:commission_ledger",
            )
        )

        # 5. Competitive
        comp_flag = float(getattr(row, "competitor_mention_flag", 0.0))
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.COMPETITIVE,
                metric_name="competitor_mention_flag",
                observed_value=comp_flag,
                baseline_value=0.0,
                relative_delta=round(comp_flag, 4),
                hazard_weight=self.weights[SignalFamily.COMPETITIVE],
                citation_ref="DP10:partner_comms",
            )
        )

        return contributions

    def get_top_driver(self, contributions: Sequence[SignalContribution]) -> SignalContribution:
        """Determines the single most significant risk driver (highest positive impact)."""

        # Sort by (hazard_weight * relative_delta) descending
        def impact_score(c: SignalContribution) -> float:
            if c.signal_family == SignalFamily.COMPETITIVE and c.observed_value > 0:
                return 999.0  # Immediate critical priority
            return c.hazard_weight * c.relative_delta

        sorted_contribs = sorted(contributions, key=impact_score, reverse=True)
        return sorted_contribs[0]
