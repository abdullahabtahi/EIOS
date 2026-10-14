"""Daily partner behaviour: logins, referrals, first deposits, deposit volume, payout latency and commissions.

Each partner has a baseline set by tier and an activity multiplier shaped by its planted driver: a churn driver
decays from its onset day, a holiday dip falls and recovers, a grower climbs. Weekends are quieter. The engines read
the rows; the driver itself never leaves this module.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from eios.foundry.scenarios.partner_config import Driver, PartnerWorldConfig, Tier

# Baselines per tier: logins a day, referrals a day, average first deposit (USD). [ASSUMPTION]
_BASE = {
    Tier.SUPER.value: (45.0, 9.0, 900.0),
    Tier.MASTER.value: (20.0, 4.0, 600.0),
    Tier.AFFILIATE.value: (8.0, 1.5, 400.0),
}
_WEEKEND = 0.35
_BOOK_DAYS = 6.0  # recurring deposits from the existing book, in days of first deposits
_COMMISSION_RATE = 0.035
_HOLIDAY_DAYS = 8
_LATENCY_NORMAL = (0.4, 1.6)  # hours
_LATENCY_FRICTION = (5.0, 9.0)


def first_day(config: PartnerWorldConfig) -> date:
    return config.as_of.date() - timedelta(days=config.history_days - 1)


def _churn_curve(days: np.ndarray, onset: int, floor: float, tau: float) -> np.ndarray:
    after = np.clip(days - onset, 0, None)
    return np.where(days < onset, 1.0, floor + (1.0 - floor) * np.exp(-after / tau))


def multiplier(driver: str, onset: int, days: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Activity relative to the partner's baseline on each day."""
    h = len(days)
    if driver == Driver.GROWING.value:
        return 1.0 + 0.4 * days / h
    if driver == Driver.SEASONAL.value:
        dip = (days >= onset) & (days < onset + _HOLIDAY_DAYS)
        return np.where(dip, 0.15, np.where(days >= onset + _HOLIDAY_DAYS, 1.15, 1.0))
    if driver == Driver.DORMANT.value:
        return 1.0 - 0.75 * np.clip((days - onset) / max(h - onset, 1), 0.0, 1.0)
    if driver == Driver.REBATE.value:
        return _churn_curve(
            days, onset, float(rng.uniform(0.45, 0.6)), float(rng.uniform(4.0, 8.0))
        )
    if driver in (Driver.CASHIER.value, Driver.POACHING.value):
        # Half decline hard, half only partly: a partial decline is harder to tell from noise.
        floor = rng.uniform(0.1, 0.35) if rng.random() < 0.5 else rng.uniform(0.4, 0.7)
        return _churn_curve(days, onset, float(floor), float(rng.uniform(3.0, 9.0)))
    return np.ones(h)


def _weekday_factor(start: date, h: int) -> np.ndarray:
    weekday = np.array([(start + timedelta(days=int(d))).weekday() for d in range(h)])
    return np.where(weekday >= 5, _WEEKEND, 1.0)


def partner_days(
    row: pd.Series, config: PartnerWorldConfig, rng: np.random.Generator
) -> pd.DataFrame:
    """One row per day of history for one partner."""
    h = config.history_days
    start = first_day(config)
    days = np.arange(h)
    logins0, refs0, ftd_size = _BASE[str(row["tier"])]
    scale = float(rng.lognormal(0.0, 0.35))
    m = multiplier(str(row["driver"]), int(row["onset_day"]), days, rng) * _weekday_factor(start, h)
    conv = float(np.clip(rng.beta(6, 14), 0.08, 0.6))
    logins = rng.poisson(logins0 * scale * m)
    referrals = rng.poisson(refs0 * scale * m)
    ftd = rng.binomial(referrals, conv)
    volume = ftd * ftd_size * rng.lognormal(0.0, 0.25, h) + (
        refs0 * scale * conv * ftd_size * _BOOK_DAYS * m * rng.lognormal(0.0, 0.15, h)
    )
    friction = (row["driver"] == Driver.CASHIER.value) & (days >= int(row["onset_day"]))
    latency = np.where(
        friction, rng.uniform(*_LATENCY_FRICTION, h), rng.uniform(*_LATENCY_NORMAL, h)
    )
    return pd.DataFrame(
        {
            "partner_id": row["partner_id"],
            "date": [start + timedelta(days=int(d)) for d in days],
            "logins": logins.astype(int),
            "referrals": referrals.astype(int),
            "ftd_count": ftd.astype(int),
            "conversion_rate": np.where(referrals > 0, ftd / np.maximum(referrals, 1), 0.0),
            "clicks": rng.poisson(np.maximum(logins, 0) * 25.0).astype(int),
            "volume_usd": np.round(volume, 2),
            "payout_latency_hours": np.round(latency, 2),
        }
    )


def commissions(days: pd.DataFrame, row: pd.Series, config: PartnerWorldConfig) -> pd.DataFrame:
    """Weekly commission payouts; a rebate dispute cuts them from its onset."""
    frame = days.assign(week=[(d - first_day(config)).days // 7 for d in days["date"]])
    weekly = frame.groupby("week").agg(volume=("volume_usd", "sum"), paid=("date", "max"))
    disputed = row["driver"] == Driver.REBATE.value
    cut_from = int(row["onset_day"]) // 7 if disputed else 10**6
    rate = np.where(weekly.index >= cut_from, _COMMISSION_RATE * 0.2, _COMMISSION_RATE)
    return pd.DataFrame(
        {
            "entry_id": [f"COM-{row['partner_id']}-{w:02d}" for w in weekly.index],
            "partner_id": row["partner_id"],
            "client_id": "",
            "basis": "REVENUE_SHARE",
            "amount": np.round(weekly["volume"].to_numpy() * rate, 2),
            "currency": "USD",
            "paid_at": [pd.Timestamp(d) + pd.Timedelta(hours=9) for d in weekly["paid"]],
        }
    )
