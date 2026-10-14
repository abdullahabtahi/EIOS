"""Plain views of a case that a read model hands to the tool port: a timeline event and a pending withdrawal."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TimelineEvent:
    at: datetime
    kind: str
    amount_usd: float | None
    detail: str


@dataclass(frozen=True)
class PendingWithdrawal:
    withdrawal_id: str
    amount_usd: float
    hours_since_deposit: float
    market_risk_pct: float
    hours_since_kyc: float
