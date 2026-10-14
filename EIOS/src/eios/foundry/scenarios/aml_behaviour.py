"""Ordinary client behaviour for the AML world: normal traders, scalpers and wealthy depositors (spec 031 FR-002).

Scalpers and wealthy clients are hard negatives. They look unusual to a naive rule (a deposit and a quick
withdrawal; very large amounts) and are legitimate, so the triage scorer has something real to suppress.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_population import token
from eios.foundry.scenarios.aml_rows import (
    DEPOSIT,
    SYMBOLS,
    WITHDRAWAL,
    trade_row,
    txn_row,
)

_ASSETS = ("CARD", "BANK", "USDT")
_ASSET_WEIGHTS = (0.75, 0.15, 0.10)
_TAIL_DAYS = 4.0  # time left after the last deposit for a later withdrawal
_RAPID_HOURS = (2.0, 60.0)
_LATER_HOURS = (96.0, 480.0)
_HOLD_MEDIAN_S = 4000.0
_DEPOSIT_SIGMA = 0.6
_PNL_CAP_SHARE = 0.4

Rows = list[dict[str, Any]]


@dataclass(frozen=True)
class Behaviour:
    deposit_share_of_income: float
    deposit_cap: float
    extra_deposits: float
    trades: float
    pnl_share: float
    withdraw_prob: float
    rapid_prob: float
    rapid_keeps_trading: bool


NORMAL = Behaviour(0.30, 3000.0, 1.5, 12.0, 0.015, 0.35, 0.06, False)
SCALPER = Behaviour(0.50, 6000.0, 1.0, 90.0, 0.004, 0.9, 0.9, True)
WEALTHY = Behaviour(0.60, 80000.0, 1.0, 20.0, 0.01, 0.5, 0.02, True)


def client_activity(
    clients: pd.DataFrame, profile: Behaviour, config: AmlWorldConfig, rng: np.random.Generator
) -> tuple[Rows, Rows]:
    """Transactions and trades for every client in `clients`, drawn from `profile`."""
    txns: Rows = []
    trades: Rows = []
    for row in clients.itertuples(index=False):
        t, tr = _one_client(row, profile, config, rng)
        txns.extend(t)
        trades.extend(tr)
    return txns, trades


def _one_client(
    row: Any, profile: Behaviour, config: AmlWorldConfig, rng: np.random.Generator
) -> tuple[Rows, Rows]:
    start = pd.Timestamp(config.as_of - timedelta(days=config.window_days))
    end = pd.Timestamp(config.as_of)
    cid, kyc = str(row.client_id), pd.Timestamp(row.kyc_approved_at)
    pay = token("pay", cid)
    amounts, times = _deposits(float(row.declared_monthly_income_usd), profile, config, start, rng)
    asset = str(rng.choice(_ASSETS, p=_ASSET_WEIGHTS))
    txns = [
        txn_row(cid, DEPOSIT, a, t, kyc=kyc, asset=asset, payment_token=pay)
        for a, t in zip(amounts, times, strict=True)
    ]
    rapid = bool(rng.random() < profile.rapid_prob)
    exit_at = _exit_time(times[0], end, rapid, profile, rng)
    if exit_at is not None:
        share = float(rng.uniform(0.9, 1.0)) if rapid else float(rng.uniform(0.4, 0.95))
        base = amounts[0] if rapid else float(amounts.sum())
        txns.append(
            txn_row(cid, WITHDRAWAL, base * share, exit_at, kyc=kyc, asset=asset, payment_token=pay)
        )
    trade_until = exit_at if rapid and exit_at is not None else end
    trades = _trades(cid, times[0], trade_until, float(amounts.sum()), profile, rapid, rng)
    return txns, trades


def _deposits(
    income: float,
    profile: Behaviour,
    config: AmlWorldConfig,
    start: pd.Timestamp,
    rng: np.random.Generator,
) -> tuple[np.ndarray, list[pd.Timestamp]]:
    count = 1 + int(rng.poisson(profile.extra_deposits))
    median = float(np.clip(profile.deposit_share_of_income * income, 25.0, profile.deposit_cap))
    amounts = np.round(rng.lognormal(np.log(median), _DEPOSIT_SIGMA, count), 2)
    hours = np.sort(rng.uniform(0.0, config.window_days * 24.0 - _TAIL_DAYS * 24.0, count))
    return amounts, [start + timedelta(hours=float(h)) for h in hours]


def _exit_time(
    first: pd.Timestamp,
    end: pd.Timestamp,
    rapid: bool,
    profile: Behaviour,
    rng: np.random.Generator,
) -> pd.Timestamp | None:
    """When the client withdraws, if at all: within 72 hours when `rapid`, else days later."""
    if rapid:
        return first + timedelta(hours=float(rng.uniform(*_RAPID_HOURS)))
    if rng.random() >= profile.withdraw_prob:
        return None
    later = first + timedelta(hours=float(rng.uniform(*_LATER_HOURS)))
    return later if later < end - timedelta(hours=1) else None


def _trades(
    cid: str,
    first: pd.Timestamp,
    until: pd.Timestamp,
    deposited: float,
    profile: Behaviour,
    rapid: bool,
    rng: np.random.Generator,
) -> Rows:
    """Directional trading with real exposure. A rapid exit without `rapid_keeps_trading` is a cancelled deposit."""
    if rapid and not profile.rapid_keeps_trading:
        return []
    count = int(rng.poisson(profile.trades))
    span = max((until - first).total_seconds(), 1.0)
    opens = np.sort(rng.uniform(0.0, span, count))
    scale = profile.pnl_share * deposited
    pnl = np.clip(
        rng.standard_t(3, count) * scale, -_PNL_CAP_SHARE * deposited, _PNL_CAP_SHARE * deposited
    )
    hold = rng.lognormal(np.log(_HOLD_MEDIAN_S), 0.8, count)
    symbols = rng.choice(SYMBOLS, size=count)
    return [
        trade_row(
            cid,
            first + timedelta(seconds=float(o)),
            float(h),
            float(p),
            str(s),
            float(rng.uniform(0.01, 2.0)),
        )
        for o, h, p, s in zip(opens, hold, pnl, symbols, strict=True)
    ]
