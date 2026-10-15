"""The geo engine: IP-versus-KYC mismatch and risky cross-border corridors, scored against what was planted.

Deterministic rules over the world's `geo_flows`, the transactions and the clients, with jurisdiction tiers passed in
from the reference layer. One statistical test serves both lenses: a client is flagged when this many foreign logins (or
elevated-tier payments) would be very unlikely at the population's base rate. Whether a client is *assessable* follows
from the same statistics: could every one of its events being foreign or elevated reach significance? A client with
too few events to ever be significant is reported as not assessable, not as clean. Nothing reads the truth until the last
step, and only to score the engine `[MEASURED]`; a figure that cannot be measured is `None`, never zero.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import binom

from eios.foundry.scenarios.aml_geo import GeoTruth
from eios.foundry.scenarios.aml_world import AmlWorld

# [ASSUMPTION] stated here so the evaluation, not the code, decides whether they hold.
ALPHA = 1e-3  # chance of a pattern this extreme at the base rate; about 6 chance flags among 6000 clients
MIN_HITS = 2  # a single foreign login or elevated payment never flags a client on its own
SCORE_CAP = 6.0  # -log10(p) is capped here when normalised into a 0..1 score
TOP_K = 50
_TIER_RANK = {"low": 0, "medium": 1, "high": 2}
_TIER_WEIGHT = {"high": 1.0, "medium": 0.5}
_MONEY_STATUSES = ("COMPLETED", "PENDING")
_DEPOSIT = "DEPOSIT"


@dataclass(frozen=True)
class GeoQuality:
    """How the geo lenses did against the planted truth `[MEASURED]`; None where it could not be measured."""

    clients: int
    mismatch_flagged: int
    mismatch_assessable: int
    mismatch_precision: float
    mismatch_recall: float
    mismatch_recall_assessable: float
    mismatch_recall_malicious: float
    corridor_flagged: int | None
    corridor_assessable: int | None
    corridor_precision: float | None
    corridor_recall: float | None
    corridor_recall_assessable: float | None
    planted_corridors_elevated: float | None
    top_k: int
    precision_at_k: float
    base_rate: float
    lift_at_k: float
    build_seconds: float


@dataclass(frozen=True)
class GeoSnapshot:
    world: AmlWorld
    clients: pd.DataFrame
    corridors: pd.DataFrame
    tiers: Mapping[str, str]
    quality: GeoQuality | None


def _events(world: AmlWorld, tiers: Mapping[str, str]) -> pd.DataFrame:
    if world.geo_flows is None:
        raise ValueError("this world carries no geo flows")
    txn = world.transactions[["txn_id", "transaction_type", "amount", "status"]]
    home = world.clients[["client_id", "country"]].rename(columns={"country": "kyc_country"})
    df = world.geo_flows.merge(txn, on="txn_id").merge(home, on="client_id")
    df = df[df["status"].isin(_MONEY_STATUSES)].copy()
    deposit = df["transaction_type"] == _DEPOSIT
    df["foreign_ip"] = df["ip_country"] != df["kyc_country"]
    cross = df["instrument_country"] != df["kyc_country"]
    df["origin"] = np.where(deposit, df["instrument_country"], df["kyc_country"])
    df["destination"] = np.where(deposit, df["kyc_country"], df["instrument_country"])
    hop_tier = df["instrument_country"].map(tiers).fillna("low")
    df["weight"] = np.where(cross, hop_tier.map(_TIER_WEIGHT).fillna(0.0), 0.0)
    df["elevated"] = df["weight"] > 0
    return df


def _test(hits: pd.Series, events: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """(p-value, flagged, assessable) of `hits` out of `events` against the population rate of hits."""
    rate = hits.sum() / max(events.sum(), 1)
    tail = pd.Series(np.where(events > 0, binom.sf(hits - 1, events, rate), 1.0), index=hits.index)
    flagged = (hits >= MIN_HITS) & (tail < ALPHA)
    ceiling = pd.Series(
        np.where(events >= MIN_HITS, rate ** events.clip(lower=1), 1.0), index=hits.index
    )
    return tail, flagged, ceiling < ALPHA


def _score(p: pd.Series) -> pd.Series:
    return np.minimum(-np.log10(np.maximum(p, 1e-12)), SCORE_CAP) / SCORE_CAP


def _client_table(world: AmlWorld, events: pd.DataFrame) -> pd.DataFrame:
    by = events.groupby("client_id")
    table = pd.DataFrame(
        {
            "events": by.size(),
            "foreign_ip_events": by["foreign_ip"].sum(),
            "elevated_events": by["elevated"].sum(),
            "volume_usd": by["amount"].sum(),
            "risky_volume_usd": (events["amount"] * events["weight"])
            .groupby(events["client_id"])
            .sum(),
        }
    )
    top_ip = (
        events[events["foreign_ip"]]
        .groupby("client_id")["ip_country"]
        .agg(lambda s: s.mode().iat[0])
    )
    counts = ["events", "foreign_ip_events", "elevated_events", "volume_usd", "risky_volume_usd"]
    table = pd.DataFrame({"client_id": world.clients["client_id"]}).merge(
        table.join(top_ip.rename("top_foreign_ip")),
        left_on="client_id",
        right_index=True,
        how="left",
    )
    table[counts] = table[counts].fillna(0)
    events_ = table["events"].where(table["events"] > 0, np.nan)
    volume = table["volume_usd"].where(table["volume_usd"] > 0, np.nan)
    table["mismatch_share"] = (table["foreign_ip_events"] / events_).fillna(0.0)
    table["risky_share"] = (table["risky_volume_usd"] / volume).fillna(0.0)
    table["mismatch_p"], table["mismatch_flag"], table["mismatch_assessable"] = _test(
        table["foreign_ip_events"], table["events"]
    )
    table["corridor_p"], table["corridor_flag"], table["corridor_assessable"] = _test(
        table["elevated_events"], table["events"]
    )
    table["geo_risk_score"] = (
        _score(table["mismatch_p"]) * table["mismatch_flag"]
        + _score(table["corridor_p"]) * table["corridor_flag"]
    )
    return table


def _corridor_table(events: pd.DataFrame, tiers: Mapping[str, str]) -> pd.DataFrame:
    cross = events[events["origin"] != events["destination"]]
    grouped = cross.groupby(["origin", "destination"])
    table = pd.DataFrame(
        {
            "volume_usd": grouped["amount"].sum(),
            "accounts": grouped["client_id"].nunique(),
            "events": grouped.size(),
        }
    ).reset_index()
    ends = zip(
        table["origin"].map(lambda c: tiers.get(c, "low")),
        table["destination"].map(lambda c: tiers.get(c, "low")),
        strict=True,
    )
    table["tier"] = [max(pair, key=_TIER_RANK.__getitem__) for pair in ends]
    return table.sort_values("volume_usd", ascending=False, ignore_index=True)


def _ratio(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def _ids(clients: pd.DataFrame, column: str) -> frozenset[str]:
    return frozenset(clients.loc[clients[column], "client_id"])


def _quality(
    world: AmlWorld,
    truth: GeoTruth,
    clients: pd.DataFrame,
    corridors: pd.DataFrame,
    tiers: Mapping[str, str],
    seconds: float,
) -> GeoQuality:
    flagged, can_assess = _ids(clients, "mismatch_flag"), _ids(clients, "mismatch_assessable")
    planted = truth.mismatch_malicious | truth.mismatch_benign
    measured = bool(tiers)
    risky, risky_assessable = _ids(clients, "corridor_flag"), _ids(clients, "corridor_assessable")
    elevated = {(r.origin, r.destination) for r in corridors.itertuples() if r.tier != "low"}
    bad = world.truth.malicious()
    top = clients.sort_values(["geo_risk_score", "client_id"], ascending=[False, True]).head(TOP_K)
    precision_k = _ratio(len(bad & set(top["client_id"])), len(top))
    base = _ratio(len(bad), len(clients))
    return GeoQuality(
        clients=len(clients),
        mismatch_flagged=len(flagged),
        mismatch_assessable=len(can_assess),
        mismatch_precision=_ratio(len(flagged & planted), len(flagged)),
        mismatch_recall=_ratio(len(flagged & planted), len(planted)),
        mismatch_recall_assessable=_ratio(len(flagged & planted), len(planted & can_assess)),
        mismatch_recall_malicious=_ratio(
            len(flagged & truth.mismatch_malicious), len(truth.mismatch_malicious)
        ),
        corridor_flagged=len(risky) if measured else None,
        corridor_assessable=len(risky_assessable) if measured else None,
        corridor_precision=_ratio(len(risky & truth.risky_clients), len(risky))
        if measured
        else None,
        corridor_recall=_ratio(len(risky & truth.risky_clients), len(truth.risky_clients))
        if measured
        else None,
        corridor_recall_assessable=(
            _ratio(len(risky & truth.risky_clients), len(truth.risky_clients & risky_assessable))
            if measured
            else None
        ),
        planted_corridors_elevated=_ratio(
            len(truth.risky_corridors & elevated), len(truth.risky_corridors)
        )
        if measured
        else None,
        top_k=len(top),
        precision_at_k=precision_k,
        base_rate=base,
        lift_at_k=round(precision_k / base, 2) if base else 0.0,
        build_seconds=round(seconds, 2),
    )


def run_geo_engine(world: AmlWorld, tiers: Mapping[str, str]) -> GeoSnapshot:
    started = time.perf_counter()
    events = _events(world, tiers)
    clients = _client_table(world, events)
    corridors = _corridor_table(events, tiers)
    truth = world.truth.geo
    quality = (
        _quality(world, truth, clients, corridors, tiers, time.perf_counter() - started)
        if truth
        else None
    )
    return GeoSnapshot(world, clients, corridors, dict(tiers), quality)


__all__ = ["TOP_K", "GeoQuality", "GeoSnapshot", "run_geo_engine"]
