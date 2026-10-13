"""Frontline Decision Playbook Prior Recalibration Engine."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime

import numpy as np

from eios.flywheel.models import DecisionOutcomeRecord, PlaybookPolicyPrior


class PlaybookPriorUpdater:
    """Recalibrates frontline action playbook priors using empirical ledger outcomes.

    Updates empirical win-rates, expected financial payoff distributions, and
    confidence scores presented to operators in the Frontline Workstation.
    """

    def __init__(self, default_horizon: str = "60d") -> None:
        self.default_horizon = default_horizon

    def update_prior(
        self,
        policy_id: str,
        action_type: str,
        records: Sequence[DecisionOutcomeRecord],
        horizon: str | None = None,
        success_threshold: float = 0.0,
    ) -> PlaybookPolicyPrior:
        """Computes empirical win-rates, expected payoffs, and confidence ratings."""
        target_horizon = horizon or self.default_horizon
        valid_outcomes: list[float] = []

        for r in records:
            if r.action_type != action_type:
                continue

            actual: float | None = None
            if target_horizon == "30d":
                actual = r.actual_impact_30d
            elif target_horizon == "60d":
                actual = r.actual_impact_60d
            elif target_horizon == "90d":
                actual = r.actual_impact_90d

            if actual is not None:
                valid_outcomes.append(float(actual))

        n = len(valid_outcomes)
        if n == 0:
            return PlaybookPolicyPrior(
                policy_id=policy_id,
                action_type=action_type,
                empirical_win_rate=0.50,
                expected_payoff_usd=0.0,
                confidence_score=0.0,
                sample_observations=0,
                last_recalibrated_at=datetime.now(UTC),
            )

        arr = np.asarray(valid_outcomes, dtype=np.float64)
        wins = int(np.sum(arr > success_threshold))
        win_rate = float(wins / n)
        expected_payoff = float(np.mean(arr))

        # Sample-adjusted confidence score: scales with sample size and win rate
        sample_shrinkage = 1.0 - (1.0 / math.sqrt(n + 1.0))
        confidence = float(np.clip(win_rate * sample_shrinkage, 0.0, 1.0))

        return PlaybookPolicyPrior(
            policy_id=policy_id,
            action_type=action_type,
            empirical_win_rate=round(win_rate, 4),
            expected_payoff_usd=round(expected_payoff, 2),
            confidence_score=round(confidence, 4),
            sample_observations=n,
            last_recalibrated_at=datetime.now(UTC),
        )
