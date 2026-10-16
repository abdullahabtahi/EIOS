"""Login hotspots with a significance test: countries that foreign accounts log into again and again, beyond chance.

GEOG 850 (Penn State, "Location intelligence for AML") warns that density clustering finds chance patterns in
geospatial data. A count map of foreign logins would rank the Netherlands first here, because a commercial VPN exit
there carries many privacy-minded clients. This lens asks a narrower question and tests it:

- Statistic: for each login country, the returning foreign accounts, accounts living elsewhere that log in from it
  at least twice. Each account counts once, so one traveller logging in many times on a trip cannot make a hotspot
  (a first version counted repeat sessions and flagged two travel destinations: precision 0.75 `[MEASURED]`).
- Null: an account that logs in from abroad returns with one book-wide probability. It is the median of the
  per-country shares, so the countries under test do not set their own baseline.
- Decision: one-sided binomial tail per country, then Benjamini-Hochberg at a false discovery rate of 5% across all
  countries tested. A country that fails is shown as "could be chance", never as clean.
- RL-4: sessions through a hub gateway (more than `HUB_DEGREE` accounts: a carrier NAT, a commercial VPN) are left
  out before counting, as everywhere else. With them, the VPN country becomes a false hotspot; the quality record
  reports both.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import binom

FDR = 0.05  # [ASSUMPTION] the share of hotspots allowed to be chance, controlled across all countries tested
MIN_ACCOUNTS = 3  # fewer foreign accounts than this is not a pattern of a place


@dataclass(frozen=True)
class HotspotQuality:
    """How the hotspot test did against the planted ring-exit countries `[MEASURED]`."""

    tested: int
    hotspots: int
    precision: float
    recall: float
    hotspots_without_rl4: int
    precision_without_rl4: float


def _bh(p: pd.Series, q: float) -> tuple[pd.Series, pd.Series]:
    """Benjamini-Hochberg adjusted p-values and the decision at false discovery rate `q`."""
    order = p.sort_values()
    m = len(order)
    ranks = np.arange(1, m + 1)
    adjusted = np.minimum.accumulate((order.to_numpy() * m / ranks)[::-1])[::-1]
    q_values = pd.Series(np.minimum(adjusted, 1.0), index=order.index).reindex(p.index)
    return q_values, q_values <= q


def login_hotspots(
    sessions: pd.DataFrame, home: pd.Series, hubs: Collection[str] = ()
) -> pd.DataFrame:
    """One row per login country with foreign logins: accounts, repeat logins, expected, p, q, and the decision.

    `hubs` are gateway ids set aside under RL-4; pass none to see the test without it."""
    df = sessions.assign(kyc=sessions["client_id"].map(home))
    df = df[(df["ip_country"] != df["kyc"]) & ~df["gateway_id"].isin(set(hubs))]
    per_account = df.groupby(["ip_country", "client_id"]).size()
    table = pd.DataFrame(
        {
            "accounts": per_account.groupby(level=0).size(),
            "returning": (per_account >= 2).groupby(level=0).sum(),
            "sessions": per_account.groupby(level=0).sum(),
        }
    )
    table = table[table["accounts"] >= MIN_ACCOUNTS].copy()
    if table.empty:
        return table.assign(expected=0.0, p_value=1.0, q_value=1.0, hotspot=False)
    share = float((table["returning"] / table["accounts"]).median())
    share = min(
        max(share, 1.0 / (2 * table["accounts"].sum())), 0.999
    )  # never 0 or 1: a test needs room
    table["expected"] = table["accounts"] * share
    # P(X >= returning) for X ~ Binomial(accounts, share).
    table["p_value"] = binom.sf(table["returning"] - 1, table["accounts"], share)
    table["q_value"], table["hotspot"] = _bh(table["p_value"], FDR)
    return table.sort_values(["hotspot", "q_value"], ascending=[False, True])


def hotspot_quality(
    sessions: pd.DataFrame, home: pd.Series, hubs: Collection[str], planted: Collection[str]
) -> HotspotQuality:
    """The test against the countries where the rings' exits were planted, with and without RL-4."""
    truth = set(planted)
    with_rl4 = login_hotspots(sessions, home, hubs)
    without = login_hotspots(sessions, home, ())
    found, found_raw = (
        set(with_rl4.index[with_rl4["hotspot"]]),
        set(without.index[without["hotspot"]]),
    )

    def ratio(num: int, den: int) -> float:
        return round(num / den, 4) if den else 0.0

    return HotspotQuality(
        tested=len(with_rl4),
        hotspots=len(found),
        precision=ratio(len(found & truth), len(found)),
        recall=ratio(len(found & truth), len(truth)),
        hotspots_without_rl4=len(found_raw),
        precision_without_rl4=ratio(len(found_raw & truth), len(found_raw)),
    )
