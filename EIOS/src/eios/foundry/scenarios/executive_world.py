"""The seeded firm-level world behind the executive workstation (spec 034).

One row per day. A competitor's payout rate moves partner churn, churn moves first-time deposits, and first-time
deposits move net revenue; a spread series rides on the same competitor and moves nothing (a confounded placebo the
causal gate must reject). The structural coefficients are planted and kept in `ExecutiveTruth`, which only the
evaluation reads. `build_executive_world` is a pure function of the config; each concern has its own random stream.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from eios.foundry.rng import RNGManager

DEFAULT_SEED = 20261015
PAYOUT, CHURN, FTD, REVENUE, SPREAD = (
    "competitor_payout_rate",
    "partner_churn_rate",
    "ftd_count_28d",
    "net_revenue_usd",
    "avg_spread_pip",
)
SERIES = (PAYOUT, CHURN, FTD, REVENUE, SPREAD)
SEASON_DAYS = 91  # the business quarter: the one cycle the revenue series carries
TREND, SEASON_SIN, SEASON_COS = "calendar_trend", "calendar_season_sin", "calendar_season_cos"
CALENDAR = (TREND, SEASON_SIN, SEASON_COS)


@dataclass(frozen=True)
class ExecutiveTruth:
    """The coefficients the world was built with. Evaluation only; no engine reads it."""

    payout_to_churn: float = 0.90  # churn rate points per payout rate point
    churn_to_ftd: float = -28000.0  # first-time deposits per unit of churn rate
    ftd_to_revenue: float = 240.0  # USD of net revenue per first-time deposit
    spread_to_churn: float = 0.0  # the placebo: spread rides on the competitor and causes nothing


@dataclass(frozen=True)
class ExecutiveWorldConfig:
    seed: int = DEFAULT_SEED
    as_of: date = date(2026, 10, 14)
    history_days: int = (
        730  # [ASSUMPTION] two years: enough for a quarterly cycle and a rolling-origin backtest
    )
    payout_base: float = 0.55
    churn_base: float = 0.22
    ftd_base: float = 16000.0
    revenue_base: float = 3_800_000.0  # [ASSUMPTION] USD of net revenue in a trailing 28 days
    spread_base: float = 1.6
    event_onsets_back: tuple[int, ...] = (
        600,
        480,
        330,
        240,
        150,
        9,
    )  # days before as-of a competitor move starts
    event_size: float = 0.05
    event_decay_days: float = 12.0
    truth: ExecutiveTruth = ExecutiveTruth()

    def fingerprint(self) -> str:
        return f"{self.seed}-{self.as_of:%Y%m%d}-{self.history_days}-{self.event_onsets_back}-{self.event_size}"


@dataclass(frozen=True)
class ExecutiveWorld:
    config: ExecutiveWorldConfig
    days: pd.DataFrame  # `date` plus one column per series, oldest first

    @property
    def truth(self) -> ExecutiveTruth:
        return self.config.truth


def calendar_regressors(n: int) -> dict[str, np.ndarray]:
    """Trend and quarterly terms: what an analyst controls for so slow drift is not read as a causal effect."""
    t = np.arange(n, dtype=float)
    angle = 2.0 * np.pi * t / SEASON_DAYS
    return {TREND: t, SEASON_SIN: np.sin(angle), SEASON_COS: np.cos(angle)}


def _ar1(n: int, phi: float, sigma: float, rng: np.random.Generator) -> np.ndarray:
    out = np.zeros(n)
    shocks = rng.normal(0.0, sigma, n)
    for t in range(1, n):
        out[t] = phi * out[t - 1] + shocks[t]
    return out


def _events(config: ExecutiveWorldConfig) -> np.ndarray:
    """Competitor moves: a step up that decays back, planted `onsets_back` days before as-of."""
    n = config.history_days
    t = np.arange(n)
    bumps = np.zeros(n)
    for back in config.event_onsets_back:
        onset = n - 1 - back
        after = np.clip(t - onset, 0, None)
        bumps += np.where(
            t >= onset, config.event_size * np.exp(-after / config.event_decay_days), 0.0
        )
    return bumps


def build_executive_world(config: ExecutiveWorldConfig) -> ExecutiveWorld:
    streams = RNGManager(config.seed)
    n, truth = config.history_days, config.truth
    t = np.arange(n)
    payout = (
        config.payout_base
        + _ar1(n, 0.96, 0.004, streams.get_generator("exec.payout"))
        + _events(config)
    )
    dp = payout - config.payout_base
    noise = streams.get_generator("exec.noise")
    churn = config.churn_base + truth.payout_to_churn * dp + noise.normal(0.0, 0.006, n)
    ftd = (
        config.ftd_base + truth.churn_to_ftd * (churn - config.churn_base) + noise.normal(0, 220, n)
    )
    season = 90_000.0 * np.sin(
        2 * np.pi * t / SEASON_DAYS
    )  # a quarterly cycle no driver in the chain explains
    trend = config.revenue_base * 0.0002 * t
    revenue = (
        config.revenue_base
        + truth.ftd_to_revenue * (ftd - config.ftd_base)
        + season
        + trend
        + noise.normal(0.0, 45_000.0, n)
    )
    # Spread follows the competitor's move and nothing else: correlated with churn, causing none of it.
    spread = config.spread_base + 2.4 * dp + noise.normal(0.0, 0.03, n)
    first = config.as_of - timedelta(days=n - 1)
    frame = pd.DataFrame(
        {
            "date": [first + timedelta(days=int(d)) for d in t],
            PAYOUT: np.round(payout, 5),
            CHURN: np.round(churn, 5),
            FTD: np.round(ftd, 1),
            REVENUE: np.round(revenue, 2),
            SPREAD: np.round(spread, 4),
        }
    )
    return ExecutiveWorld(config=config, days=frame)
