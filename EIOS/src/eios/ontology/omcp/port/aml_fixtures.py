"""AML facts the workstation service does not hold per entity. [ILLUSTRATIVE]

`AMLWorkstationService` builds one dossier, one graph and one SAR for the entity it was written around and
returns the same content whatever id it is given. A capability must never let that pass for another account,
so these tables say which account each fixture is true for. Replaced by the warm tier in spec 025.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

DOSSIER_ENTITY = "CR84920"  # the entity the service's dossier, graph and SAR describe


@dataclass(frozen=True)
class PendingWithdrawal:
    withdrawal_id: str
    amount_usd: float
    hours_since_deposit: float
    market_risk_pct: float
    hours_since_kyc: float


PENDING_WITHDRAWALS: dict[str, PendingWithdrawal] = {
    "CR84920": PendingWithdrawal("W-84920-1", 7800.0, 2.0, 0.004, 1500.0),
    "CR91204": PendingWithdrawal("W-91204-1", 3200.0, 0.2, 0.0, 900.0),
}


@dataclass(frozen=True)
class TimelineEvent:
    at: datetime
    kind: str
    amount_usd: float | None
    detail: str


def timeline_for(entity_id: str, kyc_approved: datetime) -> list[TimelineEvent] | None:
    """Ordered events for the dossier entity: 16 deposits of 500 USD (8,000 in total), a ring link, a withdrawal."""
    if entity_id != DOSSIER_ENTITY:
        return None
    start = datetime(
        2026, 10, 12, 0, 0, tzinfo=UTC
    )  # last deposit 13:30 on the 13th, 2 hours before the withdrawal
    events = [
        TimelineEvent(kyc_approved, "KYC_APPROVED", None, "declared income verified at onboarding")
    ]
    events += [
        TimelineEvent(
            start + timedelta(minutes=150 * i), "DEPOSIT", 500.0, "USDT deposit via PA-HUB-007"
        )
        for i in range(16)
    ]
    events.append(
        TimelineEvent(
            datetime(2026, 10, 12, 6, 0, tzinfo=UTC),
            "RING_LINK",
            None,
            "shared device fingerprint with 22 linked accounts",
        )
    )
    events.append(
        TimelineEvent(
            datetime(2026, 10, 13, 15, 30, tzinfo=UTC),
            "WITHDRAWAL_REQUESTED",
            7800.0,
            "pending withdrawal W-84920-1",
        )
    )
    return sorted(events, key=lambda e: e.at)
