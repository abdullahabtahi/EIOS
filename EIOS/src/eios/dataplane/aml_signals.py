"""Raw surveillance alerts from the real detectors and four threshold rules (spec 031 FR-004, FR-005).

The rules are deliberately ordinary and noisy: most of what they raise is legitimate, which is what the triage
scorer exists to suppress. Detector output (round-trips, mule rings) is turned into alerts with features computed
from the client's own data. Thresholds are `[ASSUMPTION]` until tuned with the compliance team.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from eios.aml.models import (
    AMLAlert,
    AMLPriorityTier,
    AMLTriggerType,
    AMLTypology,
    MuleRingCluster,
)
from eios.aml.mule_ring_detector import MuleRingDetector
from eios.aml.peer_baseline import PeerBaselineEngine
from eios.aml.roundtrip_detector import RoundTripDetector
from eios.dataplane.aml_facts import peer_z
from eios.foundry.scenarios.aml_world import AmlWorld

RL4_HUB_DEGREE = (
    100  # shared nodes with more neighbours than this are collapsed out of rings (RL-4)
)
ROUND_TRIP_WINDOW_H = 72.0


@dataclass(frozen=True)
class RuleThresholds:
    """[ASSUMPTION] noisy first-line rules, as a bank's transaction monitoring would run them."""

    volume_multiple_of_income: float = 2.0
    volume_floor_usd: float = 800.0
    burst_deposits_24h: int = 4
    new_account_days: float = 7.0
    new_account_floor_usd: float = 400.0
    pass_through_ratio: float = 0.8
    pass_through_floor_usd: float = 300.0
    large_deposit_usd: float = 4000.0


def cluster_id(members: list[str]) -> str:
    """A cluster is named by who is in it, so the same ring keeps the same id on every build."""
    return "MULE-" + hashlib.sha256("|".join(sorted(members)).encode()).hexdigest()[:8].upper()


def detect_clusters(world: AmlWorld) -> list[MuleRingCluster]:
    """Mule rings over shared tokens with RL-4 hub suppression; volume is the members' real 30-day deposits."""
    detector = MuleRingDetector(max_hub_degree=RL4_HUB_DEGREE)
    raw = detector.detect_mule_rings(world.edges)
    volume = (
        world.transactions[world.transactions["transaction_type"] == "DEPOSIT"]
        .groupby("client_id")["amount"]
        .sum()
    )
    return [
        c.model_copy(
            update={
                "cluster_id": cluster_id(c.member_client_ids),
                "total_volume_usd": round(
                    float(volume.reindex(c.member_client_ids).fillna(0.0).sum()), 2
                ),
            }
        )
        for c in raw
    ]


def _alert(
    client_id: str,
    rule: str,
    trigger: AMLTriggerType,
    typology: AMLTypology,
    amount: float,
    at: datetime,
    attributes: dict[str, Any],
) -> AMLAlert:
    return AMLAlert(
        alert_id=f"ALT-{rule}-{client_id}",
        client_id=client_id,
        trigger_type=trigger,
        risk_score=0.5,
        priority_tier=AMLPriorityTier.MEDIUM,
        typology=typology,
        amount_usd=max(float(amount), 0.0),
        triggered_at=at,
        attributes={"rule": rule, **attributes},
    )


def _features(
    row: pd.Series, z: float, hours_kyc: float, mule_size: float = 1.0
) -> dict[str, float]:
    return {
        "peer_z_score": z,
        "hours_since_kyc": hours_kyc,
        "deposit_withdrawal_ratio": float(row["dw_ratio"]),
        "mule_cluster_size": mule_size,
        "market_risk_pct": float(row["market_risk"]),
    }


def _hours_since_kyc(row: pd.Series, at: pd.Timestamp) -> float:
    return float(max((at - pd.Timestamp(row["kyc_approved_at"])).total_seconds() / 3600.0, 0.0))


def rule_alerts(
    world: AmlWorld,
    facts: pd.DataFrame,
    volume_engine: PeerBaselineEngine,
    rules: RuleThresholds,
) -> list[AMLAlert]:
    """Threshold rules over 30 days of events: volume against income, burst, new account, pass-through, large deposit."""
    as_of = pd.Timestamp(world.config.as_of)
    out: list[AMLAlert] = []
    for client_id, row in facts[facts["dep_volume"] > 0].iterrows():
        cid = str(client_id)
        z = peer_z(
            volume_engine,
            cid,
            str(row["cohort_id"]),
            float(row["dep_volume"]),
            int(row["dep_count"]),
        )
        base = _features(row, z, _hours_since_kyc(row, pd.Timestamp(row["first_dep"])))
        for rule, detail in _fired(row, rules):
            out.append(
                _alert(
                    cid,
                    rule,
                    AMLTriggerType.THRESHOLD_RULE,
                    _typology(rule),
                    float(row["dep_volume"]),
                    as_of.to_pydatetime(),
                    {**base, "detail": detail},
                )
            )
    return out


def _typology(rule: str) -> AMLTypology:
    return AMLTypology.STRUCTURING if rule == "VOLUME_VS_INCOME" else AMLTypology.RAPID_MOVEMENT


def _fired(row: pd.Series, rules: RuleThresholds) -> list[tuple[str, str]]:
    volume, income = float(row["dep_volume"]), float(row["declared_monthly_income_usd"])
    fired: list[tuple[str, str]] = []
    if volume >= max(rules.volume_multiple_of_income * income, rules.volume_floor_usd):
        fired.append(
            (
                "VOLUME_VS_INCOME",
                f"30-day deposits {volume / max(income, 1.0):.1f}x declared monthly income",
            )
        )
    if (
        float(row["dw_ratio"]) >= rules.pass_through_ratio
        and volume >= rules.pass_through_floor_usd
    ):
        fired.append(("PASS_THROUGH", f"{float(row['dw_ratio']):.0%} of deposits withdrawn"))
    if int(row["dep_count"]) >= rules.burst_deposits_24h and _burst(row):
        fired.append(("DEPOSIT_BURST", f"{int(row['dep_count'])} deposits inside a day"))
    return fired


def _burst(row: pd.Series) -> bool:
    span = pd.Timestamp(row["last_dep"]) - pd.Timestamp(row["first_dep"])
    return bool(span <= timedelta(hours=24))


def new_account_alerts(
    world: AmlWorld, facts: pd.DataFrame, volume_engine: PeerBaselineEngine, rules: RuleThresholds
) -> list[AMLAlert]:
    """Deposits within days of KYC approval above a floor."""
    tx = world.transactions
    dep = tx[tx["transaction_type"] == "DEPOSIT"].copy()
    dep["age_h"] = (dep["timestamp"] - dep["kyc_approved_at"]).dt.total_seconds() / 3600.0
    young = dep[
        (dep["age_h"] <= rules.new_account_days * 24.0)
        & (dep["amount"] >= rules.new_account_floor_usd)
    ]
    first = young.sort_values("timestamp").groupby("client_id").head(1)
    out: list[AMLAlert] = []
    for rec in first.itertuples(index=False):
        row = facts.loc[str(rec.client_id)]
        z = peer_z(
            volume_engine,
            str(rec.client_id),
            str(row["cohort_id"]),
            float(row["dep_volume"]),
            int(row["dep_count"]),
        )
        out.append(
            _alert(
                str(rec.client_id),
                "NEW_ACCOUNT",
                AMLTriggerType.THRESHOLD_RULE,
                AMLTypology.RAPID_MOVEMENT,
                float(rec.amount),
                pd.Timestamp(rec.timestamp).to_pydatetime(),
                {
                    **_features(row, z, max(float(rec.age_h), 0.0)),
                    "detail": f"deposit {float(rec.age_h):.0f} hours after KYC approval",
                },
            )
        )
    return out


def large_deposit_alerts(
    world: AmlWorld, facts: pd.DataFrame, rules: RuleThresholds
) -> list[AMLAlert]:
    """A single deposit above the large-deposit floor."""
    tx = world.transactions
    big = tx[(tx["transaction_type"] == "DEPOSIT") & (tx["amount"] >= rules.large_deposit_usd)]
    out: list[AMLAlert] = []
    for rec in (
        big.sort_values("amount", ascending=False)
        .groupby("client_id")
        .head(1)
        .itertuples(index=False)
    ):
        row = facts.loc[str(rec.client_id)]
        out.append(
            _alert(
                str(rec.client_id),
                "LARGE_DEPOSIT",
                AMLTriggerType.THRESHOLD_RULE,
                AMLTypology.NONE,
                float(rec.amount),
                pd.Timestamp(rec.timestamp).to_pydatetime(),
                {
                    **_features(row, 0.0, _hours_since_kyc(row, pd.Timestamp(rec.timestamp))),
                    "detail": f"single deposit of {float(rec.amount):,.0f} USD",
                },
            )
        )
    return out


def round_trip_alerts(
    world: AmlWorld, facts: pd.DataFrame, peers: PeerBaselineEngine
) -> list[AMLAlert]:
    """Deposit, micro trades, withdrawal inside 72 hours. Pairs without a trade are cancelled deposits, not wash."""
    events = _candidate_events(world)
    if events.empty:
        return []
    found = RoundTripDetector().detect_roundtrips(events, window_hours=ROUND_TRIP_WINDOW_H)
    out: list[AMLAlert] = []
    for rt in found:
        if rt.trade_count < 1:
            continue
        row = facts.loc[rt.client_id]
        z = peer_z(
            peers, rt.client_id, str(row["cohort_id"]), rt.deposit_amount_usd, int(row["dep_count"])
        )
        features = {
            "peer_z_score": z,
            "hours_since_kyc": rt.hours_since_kyc,
            "deposit_withdrawal_ratio": rt.withdrawal_amount_usd / max(rt.deposit_amount_usd, 1.0),
            "mule_cluster_size": 1.0,
            "market_risk_pct": rt.market_risk_pct,
            "detail": f"{rt.trade_count} trades, net P&L {rt.net_pl_usd:+.2f} USD, held {rt.holding_duration_seconds / 60:.0f} min",
            "deposit_txn_id": rt.deposit_txn_id,
            "withdrawal_txn_id": rt.withdrawal_txn_id,
        }
        out.append(
            _alert(
                rt.client_id,
                "ROUND_TRIP",
                AMLTriggerType.ROUND_TRIP_SEQUENCE,
                AMLTypology.MICRO_PNL_WASH,
                rt.deposit_amount_usd,
                _last_event(world, rt.client_id),
                features,
            )
        )
    return out


def _last_event(world: AmlWorld, client_id: str) -> datetime:
    tx = world.transactions
    latest: datetime = pd.Timestamp(
        tx.loc[tx["client_id"] == client_id, "timestamp"].max()
    ).to_pydatetime()
    return latest


def _candidate_events(world: AmlWorld) -> pd.DataFrame:
    """Events of clients that have a deposit followed by a withdrawal inside the window; others cannot round-trip."""
    tx = world.transactions
    dep = tx[tx["transaction_type"] == "DEPOSIT"][["client_id", "timestamp"]]
    wd = tx[tx["transaction_type"] == "WITHDRAWAL"][["client_id", "timestamp"]]
    pairs = dep.merge(wd, on="client_id", suffixes=("_dep", "_wd"))
    gap = (pairs["timestamp_wd"] - pairs["timestamp_dep"]).dt.total_seconds() / 3600.0
    candidates = set(pairs.loc[(gap > 0) & (gap <= ROUND_TRIP_WINDOW_H), "client_id"])
    money = tx[tx["client_id"].isin(candidates)].rename(columns={"transaction_type": "event_type"})
    trades = world.trades[world.trades["client_id"].isin(candidates)].assign(event_type="TRADE")
    return pd.concat([money, trades], ignore_index=True)


def mule_alerts(
    world: AmlWorld,
    facts: pd.DataFrame,
    clusters: list[MuleRingCluster],
    volume_engine: PeerBaselineEngine,
) -> list[AMLAlert]:
    """One alert per member of every syndicate-sized ring; the features are the member's own."""
    out: list[AMLAlert] = []
    as_of = pd.Timestamp(world.config.as_of).to_pydatetime()
    for cluster in clusters:
        if not cluster.is_syndicate:
            continue
        for cid in cluster.member_client_ids:
            row = facts.loc[cid]
            z = peer_z(
                volume_engine,
                cid,
                str(row["cohort_id"]),
                float(row["dep_volume"]),
                int(row["dep_count"]),
            )
            features = {
                **_features(
                    row,
                    z,
                    _hours_since_kyc(row, pd.Timestamp(row["first_dep"])),
                    float(cluster.cluster_size),
                ),
                "detail": cluster.plain_language_explanation,
                "cluster_id": cluster.cluster_id,
            }
            out.append(
                _alert(
                    cid,
                    "MULE_RING",
                    AMLTriggerType.MULE_RING_CLUSTER,
                    AMLTypology.MULE_SYNDICATE,
                    float(row["dep_volume"]),
                    as_of,
                    features,
                )
            )
    return out
