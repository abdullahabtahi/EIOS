"""Referred-account trades: background trading, plus opposite-trading pairs planted across sibling affiliates.

A planted pair is two accounts referred by two different sub-affiliates of the same master, trading the same symbol
in opposite directions seconds apart with near-equal size, so the P&L nets out and only the commission remains.
The fraud pair detector must find them among the background trades.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

from eios.foundry.scenarios.partner_config import STORY_PARTNER, PartnerWorldConfig, Tier

TRADE_COLUMNS = (
    "trade_id",
    "account_id",
    "partner_id",
    "symbol",
    "direction",
    "lots",
    "timestamp",
    "pnl_usd",
    "commission_usd",
)
_SYMBOLS = ("Volatility 75", "Boom 1000", "EURUSD", "XAUUSD")
_PAIR_SYMBOL = "Boom 1000"
_WINDOW_DAYS = 14
_COMMISSION = 5.0
_ACCOUNT_LOW, _ACCOUNT_HIGH = 700000, 799999


@dataclass(frozen=True)
class PlantedPair:
    master_id: str
    account_a: str
    partner_a: str
    account_b: str
    partner_b: str


def _sibling_sets(roster: pd.DataFrame) -> list[tuple[str, list[str]]]:
    """Masters with at least two sub-affiliates, the story partner first."""
    kids = roster[roster["parent_id"] != ""].groupby("parent_id")["partner_id"].apply(list)
    sets = [(str(m), sorted(map(str, c))) for m, c in kids.items() if len(c) >= 2]
    return sorted(sets, key=lambda s: (s[0] != STORY_PARTNER, s[0]))


def _accounts(n: int, rng: np.random.Generator) -> list[str]:
    return [
        f"CR{v}" for v in rng.choice(np.arange(_ACCOUNT_LOW, _ACCOUNT_HIGH), size=n, replace=False)
    ]


def _background(
    roster: pd.DataFrame, config: PartnerWorldConfig, ids: list[str], rng: np.random.Generator
) -> list[dict[str, object]]:
    partners = roster[roster["tier"] != Tier.SUPER.value]["partner_id"].to_numpy()
    start = config.as_of - timedelta(days=_WINDOW_DAYS)
    rows: list[dict[str, object]] = []
    for account in ids:
        partner = str(rng.choice(partners))
        for _ in range(int(rng.integers(5, 16))):
            lots = float(np.round(rng.lognormal(0.0, 0.6), 2))
            rows.append(
                {
                    "account_id": account,
                    "partner_id": partner,
                    "symbol": str(rng.choice(_SYMBOLS)),
                    "direction": str(rng.choice(("BUY", "SELL"))),
                    "lots": max(lots, 0.01),
                    "timestamp": start
                    + timedelta(seconds=float(rng.uniform(0, _WINDOW_DAYS * 86400))),
                    "pnl_usd": float(np.round(rng.normal(0.0, 40.0), 2)),
                    "commission_usd": _COMMISSION,
                }
            )
    return rows


def _pair(
    pair: PlantedPair, config: PartnerWorldConfig, rng: np.random.Generator
) -> list[dict[str, object]]:
    start = config.as_of - timedelta(days=_WINDOW_DAYS)
    rows: list[dict[str, object]] = []
    for _ in range(int(rng.integers(10, 19))):
        at = start + timedelta(seconds=float(rng.uniform(0, _WINDOW_DAYS * 86400)))
        lots = float(np.round(rng.uniform(0.5, 3.0), 2))
        pnl = float(np.round(rng.normal(0.0, 120.0), 2))
        buy_first = bool(rng.random() < 0.5)
        for account, partner, direction, sign, lag in (
            (pair.account_a, pair.partner_a, "BUY" if buy_first else "SELL", 1.0, 0.0),
            (
                pair.account_b,
                pair.partner_b,
                "SELL" if buy_first else "BUY",
                -1.0,
                float(rng.uniform(0.4, 4.0)),
            ),
        ):
            rows.append(
                {
                    "account_id": account,
                    "partner_id": partner,
                    "symbol": _PAIR_SYMBOL,
                    "direction": direction,
                    "lots": float(np.round(lots * rng.uniform(0.97, 1.03), 2)),
                    "timestamp": at + timedelta(seconds=lag),
                    "pnl_usd": sign * pnl + float(np.round(rng.normal(0.0, 2.0), 2)),
                    "commission_usd": _COMMISSION,
                }
            )
    return rows


def build_trades(
    roster: pd.DataFrame, config: PartnerWorldConfig, rng: np.random.Generator
) -> tuple[pd.DataFrame, tuple[PlantedPair, ...]]:
    sets = _sibling_sets(roster)[: config.n_collusive_pairs]
    ids = _accounts(config.background_accounts + 2 * len(sets), rng)
    pairs = tuple(
        PlantedPair(master, ids[2 * i], kids[0], ids[2 * i + 1], kids[1])
        for i, (master, kids) in enumerate(sets)
    )
    rows = _background(roster, config, ids[2 * len(sets) :], rng)
    for p in pairs:
        rows.extend(_pair(p, config, rng))
    frame = pd.DataFrame(rows).sort_values("timestamp", kind="stable").reset_index(drop=True)
    frame.insert(0, "trade_id", [f"T-{i:06d}" for i in range(len(frame))])
    return frame[list(TRADE_COLUMNS)], pairs
