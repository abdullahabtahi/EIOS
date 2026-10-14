"""Per-partner evidence read from the world's rows: payout latency, complaints, rivals named, and the driver they add up to.

The driver here is inferred from data the partner manager can see (signals the hazard model scored, payout times,
messages); it is never the planted label. Root-cause text carries no numbers, so a figure always comes from a
field with a unit, never from prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from eios.churn.models import SignalContribution, SignalFamily
from eios.foundry.scenarios.partner_world import PartnerWorld

NEGATIVE = ("NEGATIVE", "ESCALATED")
RECENT_DAYS = 14
_BASELINE_DAYS = 28
_LATENCY_ALERT_HOURS = 3.0  # [ASSUMPTION] median payout time that counts as friction
_COMMISSION_CUT = -0.5
_LOGIN_DECAY = 0.3
_HIGH_RISK = 0.5
_FAMILY_CAUSE = {
    SignalFamily.BEHAVIORAL: ("ENGAGEMENT_DECAY", "Logins and first deposits declining"),
    SignalFamily.COMMUNICATION: ("ENGAGEMENT_DECAY", "Negative messages from the partner"),
    SignalFamily.FINANCIAL: ("COMMERCIAL_REBATE", "Commission falling"),
    SignalFamily.COMPETITIVE: ("COMPETITIVE_POACHING", "Rival mentioned in messages"),
}
_RIVAL = re.compile(r"(Competitor [A-Z][a-z]+)")


class DriverCode:
    CASHIER = "OPERATIONAL_CASHIER"
    POACHING = "COMPETITIVE_POACHING"
    REBATE = "COMMERCIAL_REBATE"
    DECAY = "ENGAGEMENT_DECAY"
    SEASONAL = "CYCLICAL"
    STABLE = "STABLE"


@dataclass(frozen=True)
class PartnerEvidence:
    partner_id: str
    payout_latency_hours: float  # median over the last 14 days
    baseline_latency_hours: float  # median over the 28 days before that
    negative_messages: int
    payout_complaints: int
    rival: str | None
    driver: str
    root_cause: str


def _latency(days: pd.DataFrame, as_of: pd.Timestamp) -> tuple[pd.Series, pd.Series]:
    dates = pd.to_datetime(days["date"])
    recent_start = as_of - timedelta(days=RECENT_DAYS)
    base_start = recent_start - timedelta(days=_BASELINE_DAYS)
    recent = days[dates > recent_start].groupby("partner_id")["payout_latency_hours"].median()
    base = (
        days[(dates > base_start) & (dates <= recent_start)]
        .groupby("partner_id")["payout_latency_hours"]
        .median()
    )
    return recent, base


def _strongest(contributions: tuple[SignalContribution, ...]) -> tuple[str, str]:
    """The signal family carrying the most weight in the explainer's attribution."""
    top = max(contributions, key=lambda c: c.hazard_weight * c.relative_delta)
    return _FAMILY_CAUSE.get(
        top.signal_family, (DriverCode.DECAY, "Logins and first deposits declining")
    )


def _driver(
    row: pd.Series,
    latency: float,
    payout_complaints: int,
    rival: str | None,
    contributions: tuple[SignalContribution, ...],
) -> tuple[str, str]:
    if bool(row.get("seasonal_dip_flag", False)):
        return DriverCode.SEASONAL, "Holiday dip that has recovered"
    if float(row["competitor_mention_flag"]) > 0 and rival:
        return DriverCode.POACHING, f"Rival offer reported ({rival})"
    if latency >= _LATENCY_ALERT_HOURS:
        return DriverCode.CASHIER, "Payout delays on referred clients' withdrawals"
    if float(row["commission_velocity_30d"]) <= _COMMISSION_CUT:
        return DriverCode.REBATE, "Commission cut disputed by the partner"
    if float(row["login_velocity_decay_3w"]) >= _LOGIN_DECAY:
        return DriverCode.DECAY, "Logins and first deposits declining"
    if float(row["hazard_probability_30d"]) >= _HIGH_RISK and contributions:
        return _strongest(contributions)
    if payout_complaints:
        return DriverCode.STABLE, "Stable activity; one payout complaint on file"
    return DriverCode.STABLE, "Stable activity"


def build_evidence(
    world: PartnerWorld,
    scored: pd.DataFrame,
    contributions: dict[str, tuple[SignalContribution, ...]],
) -> dict[str, PartnerEvidence]:
    as_of = pd.Timestamp(world.config.as_of.date())
    recent, base = _latency(world.days, as_of)
    msgs = world.messages
    negative = msgs[msgs["sentiment"].isin(NEGATIVE)].groupby("partner_id").size()
    payout = msgs[msgs["topic"] == "payout_delay"].groupby("partner_id").size()
    rivals = (
        msgs[msgs["topic"] == "rival_offer"]
        .assign(rival=lambda f: f["text"].str.extract(_RIVAL, expand=False))
        .dropna(subset=["rival"])
        .groupby("partner_id")["rival"]
        .last()
    )
    out: dict[str, PartnerEvidence] = {}
    for pid, row in scored.iterrows():
        key = str(pid)
        latency = round(float(recent.get(key, 0.0)), 2)
        complaints = int(payout.get(key, 0))
        rival = rivals.get(key)
        driver, cause = _driver(row, latency, complaints, rival, contributions.get(key, ()))
        out[key] = PartnerEvidence(
            partner_id=key,
            payout_latency_hours=latency,
            baseline_latency_hours=round(float(base.get(key, 0.0)), 2),
            negative_messages=int(negative.get(key, 0)),
            payout_complaints=complaints,
            rival=rival,
            driver=driver,
            root_cause=cause,
        )
    return out
