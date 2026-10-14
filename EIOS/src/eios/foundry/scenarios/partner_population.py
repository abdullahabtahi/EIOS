"""The partner roster: identity, tier, market, tenure, referral parent and the planted driver (spec 032 FR-001).

The 21 named partners keep their identities; the rest are generated. Drivers are assigned here and only the
signal generators read them, so the engines see behaviour, never labels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from eios.foundry.scenarios.partner_config import (
    CHURN_DRIVERS,
    COMPETITORS,
    MARKETS,
    NAMED,
    REGION_WEIGHTS,
    REGIONS,
    TIER_WEIGHTS,
    Driver,
    PartnerWorldConfig,
    Tier,
)

ROSTER_COLUMNS = (
    "partner_id",
    "name",
    "tier",
    "region",
    "market",
    "cohort",
    "tenure_months",
    "parent_id",
    "driver",
    "onset_day",
    "competitor",
)
_PREFIX = (
    "Prime",
    "Apex",
    "Delta",
    "Summit",
    "Harbor",
    "Vertex",
    "Crest",
    "Atlas",
    "Nova",
    "Meridian",
)
_SUFFIX = (
    "Introducers",
    "Trading Club",
    "FX Partners",
    "Signals Group",
    "Affiliates",
    "Markets Desk",
)
_TIERS = (Tier.SUPER, Tier.MASTER, Tier.AFFILIATE)
_ID_LOW, _ID_HIGH = 1000, 9999


def _generated_ids(config: PartnerWorldConfig, rng: np.random.Generator) -> list[str]:
    taken = {p.partner_id for p in NAMED}
    pool = rng.permutation(np.arange(_ID_LOW, _ID_HIGH + 1))
    return [f"PTR-{n}" for n in pool if f"PTR-{n}" not in taken][: config.n_partners - len(NAMED)]


def _drivers(n: int, config: PartnerWorldConfig, rng: np.random.Generator) -> list[Driver]:
    churn = (Driver.CASHIER, Driver.POACHING, Driver.REBATE, Driver.DORMANT)
    n_churn = round(n * config.churn_share)
    n_seasonal = round(n * config.seasonal_share)
    n_growing = round(n * config.growing_share)
    planted = [
        *(churn[i % len(churn)] for i in range(n_churn)),
        *(Driver.SEASONAL for _ in range(n_seasonal)),
        *(Driver.GROWING for _ in range(n_growing)),
    ]
    drivers = [*planted, *(Driver.STABLE for _ in range(n - len(planted)))]
    return [drivers[i] for i in rng.permutation(n)]


def _generated(config: PartnerWorldConfig, rng: np.random.Generator) -> pd.DataFrame:
    ids = _generated_ids(config, rng)
    n = len(ids)
    regions = rng.choice(REGIONS, size=n, p=REGION_WEIGHTS)
    tiers = rng.choice(np.array([t.value for t in _TIERS]), size=n, p=TIER_WEIGHTS)
    markets = [str(rng.choice(MARKETS[str(r)])) for r in regions]
    names = [f"{m} {rng.choice(_PREFIX)} {rng.choice(_SUFFIX)}" for m in markets]
    return pd.DataFrame(
        {
            "partner_id": ids,
            "name": names,
            "tier": tiers,
            "region": regions,
            "market": [f"{r} ({m})" for r, m in zip(regions, markets, strict=True)],
            "cohort": [
                f"{r} {t.split('_', 2)[-1].title()}" for r, t in zip(regions, tiers, strict=True)
            ],
            "driver": [d.value for d in _drivers(n, config, rng)],
        }
    )


def _named() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "partner_id": [p.partner_id for p in NAMED],
            "name": [p.name for p in NAMED],
            "tier": [p.tier.value for p in NAMED],
            "region": [p.region for p in NAMED],
            "market": [p.market for p in NAMED],
            "cohort": [p.cohort for p in NAMED],
            "driver": [p.driver.value for p in NAMED],
        }
    )


def _plant_cohort(
    frame: pd.DataFrame, config: PartnerWorldConfig, rng: np.random.Generator
) -> pd.DataFrame:
    """Turn `cohort_size` stable partners of one region into a synchronized poaching wave."""
    named = {p.partner_id for p in NAMED}
    pool = frame[
        (frame["region"] == config.cohort_region)
        & (frame["driver"] == Driver.STABLE.value)
        & ~frame["partner_id"].isin(named)
    ]["partner_id"].to_numpy()
    chosen = set(rng.choice(pool, size=min(config.cohort_size, len(pool)), replace=False))
    out = frame.copy()
    mask = out["partner_id"].isin(chosen)
    out.loc[mask, "driver"] = Driver.POACHING.value
    out["in_cohort"] = mask
    return out


def _onsets(
    frame: pd.DataFrame, config: PartnerWorldConfig, rng: np.random.Generator
) -> pd.DataFrame:
    """Day index (0 = first day of history) when a planted driver starts, and the rival it names."""
    out = frame.copy()
    last = config.history_days - 1
    onset = rng.integers(last - 30, last - 10, size=len(out))
    cohort_day = last - 20
    out["onset_day"] = np.where(
        out["in_cohort"], cohort_day + rng.integers(0, 3, size=len(out)), onset
    )
    churning = out["driver"].isin([d.value for d in CHURN_DRIVERS])
    out.loc[~churning & (out["driver"] != Driver.SEASONAL.value), "onset_day"] = -1
    out.loc[out["driver"] == Driver.SEASONAL.value, "onset_day"] = last - 16
    rivals = rng.choice(COMPETITORS, size=len(out))
    out["competitor"] = np.where(
        out["driver"] == Driver.POACHING.value,
        np.where(out["in_cohort"], COMPETITORS[0], rivals),
        "",
    )
    return out


def _parents(frame: pd.DataFrame, rng: np.random.Generator) -> pd.Series:
    """Masters and affiliates sit under a super partner of their own region; supers have no parent."""
    supers = frame[frame["tier"] == Tier.SUPER.value]
    by_region = {r: g["partner_id"].to_numpy() for r, g in supers.groupby("region")}
    parents: list[str] = []
    for _, row in frame.iterrows():
        heads = by_region.get(row["region"], np.array([]))
        has_parent = row["tier"] != Tier.SUPER.value and len(heads) and rng.random() < 0.7
        parents.append(str(rng.choice(heads)) if has_parent else "")
    return pd.Series(parents, index=frame.index)


def build_roster(config: PartnerWorldConfig, rng: np.random.Generator) -> pd.DataFrame:
    frame = pd.concat([_named(), _generated(config, rng)], ignore_index=True)
    frame = _plant_cohort(frame, config, rng)
    frame = _onsets(frame, config, rng)
    frame["tenure_months"] = np.clip(
        rng.lognormal(np.log(20.0), 0.7, len(frame)).round(), 2, 120
    ).astype(int)
    frame["parent_id"] = _parents(frame, rng)
    return frame[[*ROSTER_COLUMNS, "in_cohort"]]
