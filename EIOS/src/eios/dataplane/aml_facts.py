"""Per-client aggregates and peer baselines computed from the world's events (spec 031 FR-004).

Every feature a detector or the triage scorer reads comes from here, from the data, never from a constant.
"""

from __future__ import annotations

import pandas as pd

from eios.aml.peer_baseline import PeerBaselineEngine
from eios.foundry.scenarios.aml_world import AmlWorld

USDT = "USDT"
_MAX_RATIO = 3.0


def client_facts(world: AmlWorld) -> pd.DataFrame:
    """One row per client: profile plus 30-day deposit, withdrawal and trading aggregates."""
    tx = world.transactions
    deposits = tx[tx["transaction_type"] == "DEPOSIT"]
    withdrawals = tx[tx["transaction_type"] == "WITHDRAWAL"]
    by = deposits.groupby("client_id")
    facts = world.clients.set_index("client_id").copy()
    facts["dep_volume"] = by["amount"].sum()
    facts["dep_count"] = by["amount"].count()
    facts["usdt_volume"] = deposits[deposits["asset"] == USDT].groupby("client_id")["amount"].sum()
    facts["first_dep"] = by["timestamp"].min()
    facts["last_dep"] = by["timestamp"].max()
    facts["last_activity"] = tx.groupby("client_id")["timestamp"].max()
    facts["wd_volume"] = withdrawals.groupby("client_id")["amount"].sum()
    facts["net_pnl"] = world.trades.groupby("client_id")["profit_loss"].sum()
    facts["trade_count"] = world.trades.groupby("client_id")["profit_loss"].count()
    for column in ("dep_volume", "dep_count", "usdt_volume", "wd_volume", "net_pnl", "trade_count"):
        facts[column] = facts[column].fillna(0.0)
    facts["dw_ratio"] = (facts["wd_volume"] / facts["dep_volume"].clip(lower=1.0)).clip(
        upper=_MAX_RATIO
    )
    facts["market_risk"] = facts["net_pnl"].abs() / facts["dep_volume"].clip(lower=1.0)
    return facts


def _mad(values: pd.Series) -> float:
    return float((values - values.median()).abs().median())


def deposit_baseline(world: AmlWorld) -> PeerBaselineEngine:
    """Cohort baselines of a single deposit's size, by country and employment."""
    tx = world.transactions
    deposits = tx[tx["transaction_type"] == "DEPOSIT"].merge(
        world.clients[["client_id", "cohort_id"]], on="client_id"
    )
    return _engine(deposits, "amount")


def volume_baseline(facts: pd.DataFrame) -> PeerBaselineEngine:
    """Cohort baselines of 30-day deposit volume, over clients that deposited."""
    active = facts[facts["dep_volume"] > 0].reset_index()
    return _engine(active, "dep_volume")


def _engine(frame: pd.DataFrame, column: str) -> PeerBaselineEngine:
    engine = PeerBaselineEngine()
    for cohort, group in frame.groupby("cohort_id"):
        engine.register_cohort(str(cohort), float(group[column].median()), _mad(group[column]))
    return engine


def peer_z(
    engine: PeerBaselineEngine, client_id: str, cohort_id: str, amount: float, count: int
) -> float:
    """Robust z-score of `amount` against the client's cohort (cohort-only: no personal history in the window)."""
    result = engine.evaluate_client_anomaly(client_id, cohort_id, amount, transaction_count=count)
    return float(result.robust_z_score)
