"""Clients of the AML world: identity, declared income, KYC time, partner and identity tokens (spec 031 FR-001)."""

from __future__ import annotations

import hashlib
from datetime import timedelta

import numpy as np
import pandas as pd

from eios.foundry.scenarios.aml_config import (
    COUNTRIES,
    COUNTRY_INCOME_FACTOR,
    COUNTRY_WEIGHTS,
    EMPLOYMENT,
    EMPLOYMENT_WEIGHTS,
    INCOME_MEDIAN,
    STORY_IDS,
    AmlWorldConfig,
)

CLIENT_COLUMNS = (
    "client_id",
    "country",
    "employment_status",
    "declared_monthly_income_usd",
    "kyc_approved_at",
    "partner_id",
    "cohort_id",
)
_ID_LOW, _ID_HIGH = 10000, 99999
_INCOME_SIGMA = 0.55
_DIRECT_SIGNUP_SHARE = 0.3
_NEW_KYC_SHARE = 0.04
_TENURE_MEDIAN_DAYS = 240.0
_TENURE_SIGMA = 0.9


def token(kind: str, *parts: object) -> str:
    """A short deterministic identity token such as `tok_dev_1a2b3c4d5e` (hex only, so it never matches a kind word)."""
    digest = hashlib.sha256("|".join(str(p) for p in (kind, *parts)).encode()).hexdigest()[:10]
    return f"tok_{kind}_{digest}"


def client_ids(config: AmlWorldConfig, rng: np.random.Generator) -> tuple[str, ...]:
    """Unique `CR` ids; the three story accounts come first."""
    story = set(STORY_IDS)
    pool = rng.permutation(np.arange(_ID_LOW, _ID_HIGH + 1))
    drawn = [f"CR{n}" for n in pool if f"CR{n}" not in story][: config.n_clients - len(STORY_IDS)]
    return (*STORY_IDS, *drawn)


def build_clients(
    config: AmlWorldConfig, rng: np.random.Generator, ids: tuple[str, ...]
) -> pd.DataFrame:
    """One row per client; planted typologies later override the fields they need."""
    n = len(ids)
    country = rng.choice(COUNTRIES, size=n, p=COUNTRY_WEIGHTS)
    employment = rng.choice(EMPLOYMENT, size=n, p=EMPLOYMENT_WEIGHTS)
    median = np.array(
        [
            INCOME_MEDIAN[e] * COUNTRY_INCOME_FACTOR[c]
            for e, c in zip(employment, country, strict=True)
        ]
    )
    income = np.round(median * rng.lognormal(0.0, _INCOME_SIGMA, size=n), -1).clip(min=100.0)
    tenure = rng.lognormal(np.log(_TENURE_MEDIAN_DAYS), _TENURE_SIGMA, size=n)
    new_account = rng.random(n) < _NEW_KYC_SHARE
    window_start = config.as_of - timedelta(days=config.window_days)
    kyc = [
        _kyc_time(config, window_start, bool(is_new), float(days), rng)
        for is_new, days in zip(new_account, tenure, strict=True)
    ]
    partners = _partners(config, rng, n)
    frame = pd.DataFrame(
        {
            "client_id": list(ids),
            "country": country,
            "employment_status": employment,
            "declared_monthly_income_usd": income,
            "kyc_approved_at": pd.to_datetime(kyc, utc=True),
            "partner_id": partners,
        }
    )
    frame["cohort_id"] = frame["country"] + ":" + frame["employment_status"]
    return frame.loc[:, list(CLIENT_COLUMNS)]


def _kyc_time(
    config: AmlWorldConfig,
    window_start: object,
    is_new: bool,
    tenure_days: float,
    rng: np.random.Generator,
) -> pd.Timestamp:
    """KYC approval: months before the window for most clients, inside the window for a few new ones."""
    start = pd.Timestamp(window_start)
    if is_new:
        return start + timedelta(hours=float(rng.uniform(1.0, config.window_days * 24.0)))
    return start - timedelta(days=max(2.0, tenure_days))


def _partners(config: AmlWorldConfig, rng: np.random.Generator, n: int) -> list[str | None]:
    pool = config.partner_ids
    picks = rng.choice(len(pool), size=n)
    direct = rng.random(n) < _DIRECT_SIGNUP_SHARE
    return [None if is_direct else pool[int(i)] for is_direct, i in zip(direct, picks, strict=True)]
