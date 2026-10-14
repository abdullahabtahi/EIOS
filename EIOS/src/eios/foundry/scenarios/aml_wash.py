"""Planted micro-P&L wash round-trips and income-discrepancy structuring (spec 031 FR-002, FR-003).

Wash: a fresh KYC, a deposit, a handful of trades whose net P&L is within five cents, and a withdrawal of nearly the
whole deposit. Structuring: many near-equal USDT deposits worth a multiple of declared monthly income, then a large
withdrawal. `CR91204` and `CR84920` are written to the facts the documentation and golden cases already name.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from eios.foundry.scenarios.aml_config import STORY_RING_HEAD, STORY_WASH, AmlWorldConfig
from eios.foundry.scenarios.aml_planted import Planted
from eios.foundry.scenarios.aml_population import token
from eios.foundry.scenarios.aml_rows import DEPOSIT, PENDING, WITHDRAWAL, trade_row, txn_row

WASH = "WASH_ROUND_TRIP"
STRUCTURING = "INCOME_DISCREPANCY"
_WASH_KYC_HOURS = (6.0, 60.0)
_WASH_HOLD_HOURS = (2.0, 30.0)
_WASH_NET_LIMIT = 0.04
_PENDING_SHARE = 0.25


def story_wash(config: AmlWorldConfig) -> Planted:
    """CR91204: USD 3,200 in, micro trades, request to withdraw it all 12 minutes later (still pending)."""
    deposit_at = pd.Timestamp(config.as_of - timedelta(hours=4.1))
    kyc = deposit_at - timedelta(hours=900)
    pnl = (0.012, -0.008, 0.003, -0.004, 0.0)
    trades = tuple(
        trade_row(STORY_WASH, deposit_at + timedelta(minutes=2 * (i + 1)), 90.0, p, "EURUSD", 0.01)
        for i, p in enumerate(pnl)
    )
    pay = token("pay", STORY_WASH)
    txns = (
        txn_row(STORY_WASH, DEPOSIT, 3200.0, deposit_at, kyc=kyc, asset="CARD", payment_token=pay),
        txn_row(
            STORY_WASH,
            WITHDRAWAL,
            3200.0,
            deposit_at + timedelta(minutes=12),
            kyc=kyc,
            asset="CARD",
            payment_token=pay,
            status=PENDING,
            reference="W-91204-1",
        ),
    )
    overrides = {
        STORY_WASH: {
            "kyc_approved_at": kyc,
            "country": "MY",
            "employment_status": "Employed",
            "declared_monthly_income_usd": 2600.0,
        }
    }
    return Planted(txns=txns, trades=trades, overrides=overrides, tags={STORY_WASH: (WASH,)})


def wash_accounts(
    ids: tuple[str, ...], config: AmlWorldConfig, rng: np.random.Generator
) -> Planted:
    """One wash round-trip per client id; a quarter end with the withdrawal still pending."""
    parts = [
        _wash_one(cid, config, rng, pending=bool(rng.random() < _PENDING_SHARE)) for cid in ids
    ]
    return Planted(
        txns=tuple(r for p in parts for r in p.txns),
        trades=tuple(r for p in parts for r in p.trades),
        overrides={cid: f for p in parts for cid, f in p.overrides.items()},
        tags={cid: (WASH,) for cid in ids},
    )


def _wash_one(
    cid: str, config: AmlWorldConfig, rng: np.random.Generator, *, pending: bool
) -> Planted:
    latest = 2.0 if pending else config.window_days * 24.0 - 96.0
    ago = float(rng.uniform(1.0, latest)) if pending else float(rng.uniform(40.0, latest))
    deposit_at = pd.Timestamp(
        config.as_of - timedelta(hours=ago + 35.0 if not pending else ago + 3.0)
    )
    kyc = deposit_at - timedelta(hours=float(rng.uniform(*_WASH_KYC_HOURS)))
    amount = float(np.round(rng.uniform(800.0, 9000.0), -1))
    hold = float(rng.uniform(*_WASH_HOLD_HOURS)) if not pending else float(rng.uniform(0.5, 2.5))
    wd_at = deposit_at + timedelta(hours=hold)
    asset = "USDT" if rng.random() < 0.6 else "CARD"
    pay = token("pay", cid)
    status = PENDING if pending else "COMPLETED"
    txns = (
        txn_row(cid, DEPOSIT, amount, deposit_at, kyc=kyc, asset=asset, payment_token=pay),
        txn_row(
            cid,
            WITHDRAWAL,
            amount * float(rng.uniform(0.985, 1.0)),
            wd_at,
            kyc=kyc,
            asset=asset,
            payment_token=pay,
            status=status,
            reference=f"W-{cid[2:]}-1" if pending else "",
        ),
    )
    return Planted(
        txns=txns,
        trades=_micro_trades(cid, deposit_at, wd_at, rng),
        overrides={cid: {"kyc_approved_at": kyc}},
    )


def _micro_trades(
    cid: str, start: datetime | pd.Timestamp, end: datetime | pd.Timestamp, rng: np.random.Generator
) -> tuple[dict[str, object], ...]:
    """3 to 10 trades whose net P&L is within a few cents while the position is held minutes."""
    count = int(rng.integers(3, 11))
    pnl = rng.uniform(-0.02, 0.02, count)
    pnl[-1] = float(rng.uniform(-_WASH_NET_LIMIT, _WASH_NET_LIMIT)) - float(pnl[:-1].sum())
    span = max((pd.Timestamp(end) - pd.Timestamp(start)).total_seconds() - 600.0, 60.0)
    opens = np.sort(rng.uniform(120.0, span, count))
    return tuple(
        trade_row(
            cid,
            pd.Timestamp(start) + timedelta(seconds=float(o)),
            float(rng.uniform(60, 600)),
            float(p),
            "EURUSD",
            0.01,
        )
        for o, p in zip(opens, pnl, strict=True)
    )


def story_structuring(config: AmlWorldConfig) -> Planted:
    """CR84920: income USD 500 a month, 16 deposits of USD 500 in USDT in 38 hours, withdrawal of 7,800 pending."""
    kyc = pd.Timestamp(datetime(2026, 8, 14, 10, 0, tzinfo=config.as_of.tzinfo))
    start = pd.Timestamp(datetime(2026, 10, 12, 0, 0, tzinfo=config.as_of.tzinfo))
    cid, pay = STORY_RING_HEAD, token("pay", STORY_RING_HEAD)
    deposits = tuple(
        txn_row(
            cid,
            DEPOSIT,
            500.0,
            start + timedelta(minutes=150 * i),
            kyc=kyc,
            asset="USDT",
            payment_token=pay,
        )
        for i in range(16)
    )
    withdrawal = txn_row(
        cid,
        WITHDRAWAL,
        7800.0,
        pd.Timestamp(datetime(2026, 10, 13, 15, 30, tzinfo=config.as_of.tzinfo)),
        kyc=kyc,
        asset="USDT",
        payment_token=pay,
        status=PENDING,
        reference="W-84920-1",
    )
    overrides = {
        cid: {
            "kyc_approved_at": kyc,
            "country": "SG",
            "employment_status": "Self-Employed",
            "declared_monthly_income_usd": 500.0,
        }
    }
    return Planted(txns=(*deposits, withdrawal), overrides=overrides, tags={cid: (STRUCTURING,)})


def structuring_accounts(
    ids: tuple[str, ...], config: AmlWorldConfig, rng: np.random.Generator
) -> Planted:
    """Many near-equal USDT deposits worth 8 to 25 times declared income, then a large withdrawal."""
    parts = [_structuring_one(cid, config, rng) for cid in ids]
    return Planted(
        txns=tuple(r for p in parts for r in p.txns),
        overrides={cid: f for p in parts for cid, f in p.overrides.items()},
        tags={cid: (STRUCTURING,) for cid in ids},
    )


def _structuring_one(cid: str, config: AmlWorldConfig, rng: np.random.Generator) -> Planted:
    income = float(np.round(rng.uniform(250.0, 1400.0), -1))
    count = int(rng.integers(10, 25))
    each = float(np.round(income * float(rng.uniform(0.6, 1.4)), -1))
    start = pd.Timestamp(config.as_of - timedelta(hours=float(rng.uniform(60.0, 300.0))))
    kyc = start - timedelta(days=float(rng.uniform(20.0, 200.0)))
    step = float(rng.uniform(1.0, 4.0))
    pay = token("pay", cid)
    txns = [
        txn_row(
            cid,
            DEPOSIT,
            each,
            start + timedelta(hours=step * i),
            kyc=kyc,
            asset="USDT",
            payment_token=pay,
        )
        for i in range(count)
    ]
    last = start + timedelta(hours=step * count)
    txns.append(
        txn_row(
            cid,
            WITHDRAWAL,
            each * count * float(rng.uniform(0.9, 0.98)),
            last + timedelta(hours=3),
            kyc=kyc,
            asset="USDT",
            payment_token=pay,
        )
    )
    fields = {
        "kyc_approved_at": kyc,
        "declared_monthly_income_usd": income,
        "employment_status": "Self-Employed",
    }
    return Planted(txns=tuple(txns), overrides={cid: fields})
