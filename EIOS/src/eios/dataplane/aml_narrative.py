"""Timeline, pending withdrawal and SAR narrative for one account, from the world's own events (spec 031 FR-007).

Everything here is a deterministic template over computed numbers. No model writes a figure (RL-1).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from eios.aml.case_views import PendingWithdrawal, TimelineEvent
from eios.dataplane.aml_cases import AmlCase
from eios.dataplane.aml_engine import AmlSnapshot

_MAX_EVENTS = 60


def timeline(snapshot: AmlSnapshot, entity_id: str) -> list[TimelineEvent]:
    """KYC approval, every deposit and withdrawal, one trading summary, and the ring link, in time order."""
    tx = snapshot.world.transactions
    mine = tx[tx["client_id"] == entity_id]
    row = snapshot.facts.loc[entity_id]
    events = [
        TimelineEvent(
            _dt(row["kyc_approved_at"]),
            "KYC_APPROVED",
            None,
            "declared income verified at onboarding",
        )
    ]
    events += [_money_event(r) for r in mine.itertuples(index=False)]
    events += _trading_event(snapshot, entity_id)
    events += _ring_event(snapshot, entity_id)
    ordered = sorted(events, key=lambda e: e.at)
    return ordered[-_MAX_EVENTS:]


def _dt(value: Any) -> datetime:
    converted: datetime = pd.Timestamp(value).to_pydatetime()
    return converted


def _money_event(rec: Any) -> TimelineEvent:
    kind = str(rec.transaction_type)
    pending = str(rec.status) == "PENDING"
    label = "WITHDRAWAL_REQUESTED" if kind == "WITHDRAWAL" and pending else kind
    detail = f"{rec.asset} {kind.lower()}" + (f" {rec.reference}" if rec.reference else "")
    return TimelineEvent(
        pd.Timestamp(rec.timestamp).to_pydatetime(), label, float(rec.amount), detail
    )


def _trading_event(snapshot: AmlSnapshot, entity_id: str) -> list[TimelineEvent]:
    trades = snapshot.world.trades
    mine = trades[trades["client_id"] == entity_id]
    if mine.empty:
        return []
    net = float(mine["profit_loss"].sum())
    detail = f"{len(mine)} trades, net P&L {net:+.2f} USD"
    return [
        TimelineEvent(pd.Timestamp(mine["open_ts"].min()).to_pydatetime(), "TRADING", None, detail)
    ]


def _ring_event(snapshot: AmlSnapshot, entity_id: str) -> list[TimelineEvent]:
    ring = snapshot.ring_of(entity_id)
    if ring is None:
        return []
    first = snapshot.facts.loc[list(ring.member_client_ids), "first_dep"].min()
    return [
        TimelineEvent(
            pd.Timestamp(first).to_pydatetime(),
            "RING_LINK",
            None,
            f"shared device fingerprint with {ring.cluster_size - 1} linked accounts",
        )
    ]


def pending_withdrawal(snapshot: AmlSnapshot, entity_id: str) -> PendingWithdrawal | None:
    """The latest withdrawal still pending, with the hours and exposure the sentinel scores."""
    tx = snapshot.world.transactions
    mine = tx[tx["client_id"] == entity_id]
    pending = mine[(mine["transaction_type"] == "WITHDRAWAL") & (mine["status"] == "PENDING")]
    if pending.empty:
        return None
    wd = pending.sort_values("timestamp").iloc[-1]
    before = mine[(mine["transaction_type"] == "DEPOSIT") & (mine["timestamp"] <= wd["timestamp"])]
    last_dep = before["timestamp"].max() if not before.empty else wd["timestamp"]
    window = snapshot.world.trades
    held = (
        window[
            (window["client_id"] == entity_id)
            & (window["open_ts"] >= before["timestamp"].min())
            & (window["open_ts"] <= wd["timestamp"])
        ]
        if not before.empty
        else window.iloc[0:0]
    )
    exposure = abs(float(held["profit_loss"].sum())) / max(float(before["amount"].sum()), 1.0)
    return PendingWithdrawal(
        withdrawal_id=str(wd["reference"]) or f"W-{entity_id[2:]}-1",
        amount_usd=float(wd["amount"]),
        hours_since_deposit=round((wd["timestamp"] - last_dep).total_seconds() / 3600.0, 2),
        market_risk_pct=round(exposure, 5),
        hours_since_kyc=round(
            (wd["timestamp"] - wd["kyc_approved_at"]).total_seconds() / 3600.0, 1
        ),
    )


def sar_narrative(
    snapshot: AmlSnapshot, entity_id: str, case: AmlCase | None, cluster_key: str
) -> str:
    """The factual narrative of a SAR draft: who, what moved, how it links, what is pending."""
    row = snapshot.facts.loc[entity_id]
    income, volume = float(row["declared_monthly_income_usd"]), float(row["dep_volume"])
    parts = [
        f"Investigation of subject account #{entity_id} (identity cluster {cluster_key}).",
        f"Declared income of ${income:,.2f}/month against realized 30-day deposits of ${volume:,.2f} "
        f"({volume / max(income, 1.0):.1f}x), {float(row['usdt_volume']) / max(volume, 1.0):.0%} of it in USDT.",
    ]
    if float(row["wd_volume"]) > 0:
        parts.append(
            f"Withdrawals total ${float(row['wd_volume']):,.2f}, {float(row['dw_ratio']):.0%} of deposits."
        )
    if int(row["trade_count"]) > 0:
        parts.append(
            f"{int(row['trade_count'])} trades with a net P&L of ${float(row['net_pnl']):+,.2f} against ${volume:,.2f} deposited."
        )
    if case is not None and case.ring_id:
        parts.append(
            f"Linked to {case.ring_size - 1} other accounts sharing a device fingerprint and depositing in matched bursts."
        )
    pending = pending_withdrawal(snapshot, entity_id)
    if pending is not None:
        parts.append(
            f"Withdrawal {pending.withdrawal_id} of ${pending.amount_usd:,.2f} is pending, {pending.hours_since_deposit:.1f} hours after the last deposit."
        )
    return " ".join(parts)
