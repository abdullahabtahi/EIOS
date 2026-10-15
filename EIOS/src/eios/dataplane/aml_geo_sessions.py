"""Session lenses of the geo engine: shared foreign exits and impossible travel, over the world's login sessions.

Two deterministic signals, each about what a single account's transactions cannot show:

- **Shared foreign exit.** A gateway abroad that several accounts use although none of them lives in its country. One
  shared exit ties together ring members that have too few events to be judged one at a time. A gateway shared by more
  accounts than the RL-4 line is a hub (a carrier's NAT, a commercial VPN) and never ties anyone together.
- **Impossible travel.** Two consecutive sessions of one account in countries further apart than any flight could cover
  in the time between them. A jump through a hub gateway is counted but not trusted (RL-4).

Distances are between country centroids from the reference layer; without it the travel lens is not assessable and
says so. Nothing here reads the planted truth.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# [ASSUMPTION] stated here so the evaluation, not the code, decides whether they hold.
HUB_DEGREE = 100  # RL-4: shared by more accounts than this, a gateway is a hub and is suppressed
MIN_SHARED_FOREIGN = 3  # accounts that live elsewhere and use the same exit
MIN_EXIT_SESSIONS = 2  # one session through a shared exit never flags an account on its own
MAX_SPEED_KMH = 1000.0  # airliner cruise plus a margin
MIN_JUMP_KM = (
    500.0  # closer than this, country centroids are too coarse to tell a jump from a border
)
MIN_JUMPS = 2
EARTH_KM = 6371.0

LngLat = tuple[float, float]


@dataclass(frozen=True)
class SessionLenses:
    gateways: pd.DataFrame  # one row per gateway
    clients: pd.DataFrame  # one row per client
    jumps: pd.DataFrame  # one row per impossible jump
    travel_assessable: bool  # False when no country positions were given


def gateway_table(sessions: pd.DataFrame, home: pd.Series) -> pd.DataFrame:
    """Per gateway: its country, how many accounts use it, how many of them live elsewhere, and whether it is a hub."""
    df = sessions.assign(kyc=sessions["client_id"].map(home))
    df["foreign"] = df["ip_country"] != df["kyc"]
    by = df.groupby("gateway_id")
    foreign = df[df["foreign"]].groupby("gateway_id")
    table = pd.DataFrame(
        {
            "country": by["ip_country"].first(),
            "accounts": by["client_id"].nunique(),
            "sessions": by.size(),
            "foreign_accounts": foreign["client_id"].nunique(),
            "home_countries": foreign["kyc"].nunique(),
        }
    ).fillna({"foreign_accounts": 0, "home_countries": 0})
    table[["foreign_accounts", "home_countries"]] = table[
        ["foreign_accounts", "home_countries"]
    ].astype(int)
    table["hub"] = table["accounts"] > HUB_DEGREE
    table["shared_exit"] = ~table["hub"] & (table["foreign_accounts"] >= MIN_SHARED_FOREIGN)
    return table.reset_index().sort_values(
        ["shared_exit", "foreign_accounts", "gateway_id"],
        ascending=[False, False, True],
        ignore_index=True,
    )


def _km(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Great-circle distance between [lng, lat] rows, in km."""
    lng1, lat1, lng2, lat2 = (np.radians(x) for x in (a[:, 0], a[:, 1], b[:, 0], b[:, 1]))
    h = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    )
    return np.asarray(2 * EARTH_KM * np.arcsin(np.sqrt(h)), dtype=float)


_NO_JUMPS = pd.DataFrame(
    {
        "client_id": pd.Series(dtype=object),
        "from_country": pd.Series(dtype=object),
        "to_country": pd.Series(dtype=object),
        "from_ts": pd.Series(dtype="datetime64[ns, UTC]"),
        "to_ts": pd.Series(dtype="datetime64[ns, UTC]"),
        "hours": pd.Series(dtype=float),
        "km": pd.Series(dtype=int),
        "via_hub": pd.Series(dtype=bool),
    }
)


def jump_table(
    sessions: pd.DataFrame, positions: Mapping[str, LngLat], hubs: frozenset[str]
) -> pd.DataFrame:
    """Every pair of consecutive sessions of one account that no flight could connect."""
    df = sessions.sort_values(["client_id", "ts", "session_id"], ignore_index=True)
    nxt = df.shift(-1)
    pair = (df["client_id"] == nxt["client_id"]) & (df["ip_country"] != nxt["ip_country"])
    pair &= df["ip_country"].isin(positions.keys()) & nxt["ip_country"].isin(positions.keys())
    a, b = df[pair], nxt[pair]
    if a.empty:
        return _NO_JUMPS.copy()
    km = _km(
        np.array([positions[c] for c in a["ip_country"]]),
        np.array([positions[c] for c in b["ip_country"]]),
    )
    hours = (
        pd.to_datetime(b["ts"], utc=True) - pd.to_datetime(a["ts"], utc=True)
    ).dt.total_seconds().to_numpy() / 3600
    out = pd.DataFrame(
        {
            "client_id": a["client_id"].to_numpy(),
            "from_country": a["ip_country"].to_numpy(),
            "to_country": b["ip_country"].to_numpy(),
            "from_ts": a["ts"].to_numpy(),
            "to_ts": b["ts"].to_numpy(),
            "hours": np.round(hours, 2),
            "km": np.round(km).astype(int),
            "via_hub": a["gateway_id"].isin(hubs).to_numpy()
            | b["gateway_id"].isin(hubs).to_numpy(),
        }
    )
    impossible = (out["km"] >= MIN_JUMP_KM) & (
        out["km"] > MAX_SPEED_KMH * np.maximum(out["hours"], 1e-6)
    )
    return out[impossible].reset_index(drop=True)


def _client_table(
    sessions: pd.DataFrame,
    home: pd.Series,
    gateways: pd.DataFrame,
    jumps: pd.DataFrame,
    travel_assessable: bool,
) -> pd.DataFrame:
    exits = set(gateways.loc[gateways["shared_exit"], "gateway_id"])
    df = sessions.assign(kyc=sessions["client_id"].map(home))
    through = df[df["gateway_id"].isin(exits) & (df["ip_country"] != df["kyc"])]
    exit_use = (
        through.groupby(["client_id", "gateway_id"]).size().rename("exit_sessions").reset_index()
    )
    top_exit = exit_use.sort_values(
        ["client_id", "exit_sessions", "gateway_id"], ascending=[True, False, True]
    ).drop_duplicates("client_id")
    table = pd.DataFrame({"client_id": home.index}).merge(
        df.groupby("client_id").size().rename("sessions"),
        left_on="client_id",
        right_index=True,
        how="left",
    )
    table = table.merge(
        top_exit.rename(columns={"gateway_id": "exit_gateway"}), on="client_id", how="left"
    )
    trusted = jumps[~jumps["via_hub"]].groupby("client_id").size()
    table["jumps"] = table["client_id"].map(trusted).fillna(0).astype(int)
    table["hub_jumps"] = (
        table["client_id"]
        .map(jumps[jumps["via_hub"]].groupby("client_id").size())
        .fillna(0)
        .astype(int)
    )
    table["sessions"] = table["sessions"].fillna(0).astype(int)
    table["exit_sessions"] = table["exit_sessions"].fillna(0).astype(int)
    table["exit_flag"] = table["exit_sessions"] >= MIN_EXIT_SESSIONS
    table["travel_assessable"] = travel_assessable & (table["sessions"] >= 2)
    table["jump_flag"] = table["travel_assessable"] & (table["jumps"] >= MIN_JUMPS)
    return table


def run_session_lenses(
    sessions: pd.DataFrame, home: pd.Series, positions: Mapping[str, LngLat] | None
) -> SessionLenses:
    gateways = gateway_table(sessions, home)
    hubs = frozenset(gateways.loc[gateways["hub"], "gateway_id"])
    known = bool(positions)
    jumps = jump_table(sessions, positions or {}, hubs) if known else _NO_JUMPS.copy()
    return SessionLenses(
        gateways, _client_table(sessions, home, gateways, jumps, known), jumps, known
    )


def positions_from(reference: Mapping[str, Any]) -> dict[str, LngLat]:
    """Country centroids ([lng, lat]) from the reference layer's payload."""
    countries: list[dict[str, Any]] = list(reference.get("countries", []))
    return {
        str(c["iso2"]): (float(c["position"][0]), float(c["position"][1]))
        for c in countries
        if c.get("position")
    }


__all__ = [
    "HUB_DEGREE",
    "SessionLenses",
    "gateway_table",
    "jump_table",
    "positions_from",
    "run_session_lenses",
]
