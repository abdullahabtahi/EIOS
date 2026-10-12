"""Pre-registered naive threshold rule baseline detector for client AML (Constitution Principle VI).

Authoritative References:
- docs/models_and_evals.md §2
- specs/010-client-aml/research.md §7
- .specify/memory/constitution.md (Principle VI)

Pre-registered Baseline Rules:
1. Static CTR deposit threshold: amount > $10,000.0 USD
2. High 24h withdrawal velocity: withdrawal count > 3 in 24 hours
3. Rapid round-trip gap: time between deposit and withdrawal < 60.0 minutes
"""

from dataclasses import dataclass
from typing import Any
from eios.aml.models import AMLAlert


@dataclass(frozen=True)
class NaiveBaselineResult:
    alert_id: str
    client_id: str
    score: float
    flagged: bool
    reasons: list[str]


class NaiveThresholdBaseline:
    """Pre-registered static threshold rules baseline engine."""

    def __init__(
        self,
        high_amount_threshold: float = 10000.0,
        max_withdrawal_velocity_24h: int = 3,
        min_deposit_withdrawal_gap_mins: float = 60.0,
    ) -> None:
        self.high_amount_threshold = high_amount_threshold
        self.max_withdrawal_velocity_24h = max_withdrawal_velocity_24h
        self.min_deposit_withdrawal_gap_mins = min_deposit_withdrawal_gap_mins

    def score_alert(self, alert: AMLAlert) -> NaiveBaselineResult:
        """Evaluate a single AMLAlert against static threshold rules."""
        reasons: list[str] = []

        # Rule 1: Static Amount Threshold
        if alert.amount_usd > self.high_amount_threshold:
            reasons.append(f"Amount {alert.amount_usd} exceeds threshold {self.high_amount_threshold}")

        # Rule 2: Withdrawal Velocity from attributes if present
        withdrawal_count = alert.attributes.get("withdrawal_count_24h", 0)
        if withdrawal_count > self.max_withdrawal_velocity_24h:
            reasons.append(f"Withdrawal velocity {withdrawal_count} > {self.max_withdrawal_velocity_24h}")

        # Rule 3: Rapid Gap from attributes if present
        gap_mins = alert.attributes.get("deposit_withdrawal_gap_mins", 999.0)
        if gap_mins < self.min_deposit_withdrawal_gap_mins:
            reasons.append(f"Deposit-withdrawal gap {gap_mins}m < {self.min_deposit_withdrawal_gap_mins}m")

        if len(reasons) >= 2:
            score = 0.90
            flagged = True
        elif len(reasons) == 1:
            score = 0.65
            flagged = True
        else:
            score = 0.15
            flagged = False

        return NaiveBaselineResult(
            alert_id=alert.alert_id,
            client_id=alert.client_id,
            score=score,
            flagged=flagged,
            reasons=reasons,
        )

    def evaluate_queue(self, alerts: list[AMLAlert]) -> list[NaiveBaselineResult]:
        """Evaluate a queue of surveillance alerts."""
        return [self.score_alert(alert) for alert in alerts]
