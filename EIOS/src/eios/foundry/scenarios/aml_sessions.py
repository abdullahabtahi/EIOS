"""Login sessions of the seeded AML world: when each client logged in, from which country and through which gateway.

A gateway is the network egress a session came through (a home broadband line, a mobile carrier's shared address, a
hotel network, a VPN exit), named synthetically; country level only (policy P-2). Every transaction is made in a
session, so a transaction's login country is its session's country, and clients also log in without transacting.

Planted behaviour, kept apart for evaluation:

- Mule rings log in through one VPN exit per ring, abroad, interleaved with logins from home: the same exit shared by
  every member. A controller also works members' accounts from the exit within hours of the holder logging in at home,
  so the account appears in two countries closer together in time than any flight allows.
- Benign travellers make one trip: every session inside it is abroad through varied local networks, and no session
  falls close enough to the trip's ends to make a jump impossible.
- Privacy-minded clients use one commercial VPN exit shared by so many people that it is a hub, the same shape as the
  carrier-grade NAT gateways that RL-4 suppresses.
- CGNAT members log in through their carrier's shared gateway at home.
- Everyone else logs in from home, with a small share of foreign sessions from geolocation error and short trips.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from eios.foundry.scenarios.aml_config import COUNTRIES

SESSION_COLUMNS = ("session_id", "client_id", "ts", "ip_country", "gateway_id", "txn_id")

# [ASSUMPTION] every number below is a world-design choice; the evaluation, not the code, says whether a lens copes.
TRAVEL_POOL = (
    "GB", "US", "AU", "JP", "KR", "CN", "HK", "TW", "PH", "PK", "BD", "LK", "NP", "SA", "QA", "KW", "OM", "TR",
    "EG", "KE", "ZA", "GH", "MX", "AR", "CL", "PE", "DE", "FR", "NL", "CH", "IT", "ES", "CA", "IQ", "DZ", "BA",
)  # fmt: skip
RING_EXITS = (
    "NG",
    "AE",
    "IQ",
    "TR",
    "ZA",
    "PK",
)  # one VPN exit country per ring; the story rings keep NG and AE
STORY_RING_VPN = 0.9  # share of a story-ring member's sessions through the ring's exit
RING_VPN = 0.7
N_RESIDENTIAL = (
    400  # home broadband gateways per country (a line is shared by a household, rarely more)
)
BROWSE_MEAN = 5.0  # sessions without a transaction, per client over the window
BASE_FOREIGN = 0.03
CGNAT_SHARE = 0.8  # share of a CGNAT member's home sessions through the carrier gateway
PRIVACY_EXIT = ("NL", "GW-NL-V01")
N_PRIVACY = 140
PRIVACY_SHARE = 0.35
N_TRAVELLERS = 60
TRIP_DAYS = (3.0, 12.0)
CONTROLLER_SHARE = (
    0.5  # share of a ring member's home sessions followed by a controller session through the exit
)
CONTROLLER_LAG_HOURS = (0.25, 6.0)
TRIP_BUFFER = pd.Timedelta(
    hours=24
)  # no session this close to a trip's ends, so no jump into or out of it is impossible
_TRIP_TRIES = 25


@dataclass(frozen=True)
class SessionTruth:
    """What was planted in the sessions. Evaluation only; no engine reads it."""

    ring_exits: Mapping[str, frozenset[str]]  # VPN exit gateway -> ring members
    travellers: frozenset[str]  # made a trip
    trips: Mapping[str, tuple[str, str, str]]  # traveller -> (country, start, end), ISO times
    privacy_vpn: frozenset[str]


def residential(country: str, k: int) -> str:
    return f"GW-{country}-R{k:02d}"


def ring_exit(country: str, ring: int) -> str:
    return f"GW-{country}-X{ring:02d}"


def carrier(country: str, hub: int) -> str:
    return f"GW-{country}-M{hub:02d}"


def _skeleton(
    clients: pd.DataFrame,
    transactions: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """One session per transaction at its time, plus logins without one, sorted per client by time."""
    txn = pd.DataFrame(
        {
            "client_id": transactions["client_id"],
            "ts": transactions["timestamp"],
            "txn_id": transactions["txn_id"],
        }
    )
    ids = clients["client_id"].to_numpy()
    counts = rng.poisson(BROWSE_MEAN, len(ids))
    span = (end - start).total_seconds()
    offsets = pd.to_timedelta(rng.random(int(counts.sum())) * span, unit="s")
    browse = pd.DataFrame(
        {"client_id": np.repeat(ids, counts), "ts": start + offsets, "txn_id": None}
    )
    frame = pd.concat([txn, browse], ignore_index=True)
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True)
    return _ordered(frame)


def _ordered(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        ["client_id", "ts", "txn_id"], kind="stable", na_position="last", ignore_index=True
    )


def _foreign(rng: np.random.Generator, home: np.ndarray) -> np.ndarray:
    pool = np.array(sorted(set(TRAVEL_POOL) | set(COUNTRIES)))
    idx = rng.integers(0, len(pool), size=len(home))
    idx = np.where(pool[idx] == home, (idx + 1) % len(pool), idx)
    return pool[idx]


def _home_gateways(
    clients: pd.DataFrame, cgnat: tuple[tuple[str, ...], ...], rng: np.random.Generator
) -> tuple[pd.Series, pd.Series]:
    """Each client's home broadband gateway, and the carrier gateway of the CGNAT members."""
    home = clients.set_index("client_id")["country"]
    line = pd.Series(
        [
            residential(c, int(k))
            for c, k in zip(home, rng.integers(0, N_RESIDENTIAL, len(home)), strict=True)
        ],
        index=home.index,
    )
    hub: dict[str, str] = {}
    for k, group in enumerate(cgnat):
        if not group:
            continue
        # A carrier gateway sits in one country: only the members who live there reach it.
        country = home.loc[list(group)].mode().iat[0]
        hub.update(dict.fromkeys((c for c in group if home[c] == country), carrier(country, k)))
    return line, pd.Series(hub, dtype=object)


def _pick_trip(
    times: pd.Series, start: pd.Timestamp, end: pd.Timestamp, rng: np.random.Generator
) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """A trip with no session within the buffer of either end, or None when the client's sessions leave no room."""
    for _ in range(_TRIP_TRIES):
        days = pd.Timedelta(days=float(rng.uniform(*TRIP_DAYS)))
        latest = (end - start - days).total_seconds()
        if latest <= 0:
            return None
        lo = start + pd.Timedelta(seconds=float(rng.random() * latest))
        hi = lo + days
        near = ((times > lo - TRIP_BUFFER) & (times < lo)) | (
            (times > hi) & (times < hi + TRIP_BUFFER)
        )
        if not near.any() and ((times >= lo) & (times <= hi)).any():
            return lo, hi
    return None


@dataclass(frozen=True)
class SessionRoles:
    rings: tuple[tuple[str, ...], ...]
    cgnat: tuple[tuple[str, ...], ...]
    protected: Collection[str]  # scripted clients that are neither travellers nor privacy VPN users


def build_sessions(
    clients: pd.DataFrame,
    transactions: pd.DataFrame,
    roles: SessionRoles,
    window: tuple[pd.Timestamp, pd.Timestamp],
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, SessionTruth]:
    start, end = window
    frame = _skeleton(clients, transactions, start, end, rng)
    home = clients.set_index("client_id")["country"]
    line, hub = _home_gateways(clients, roles.cgnat, rng)
    kyc = frame["client_id"].map(home).to_numpy()
    n = len(frame)

    on_hub = frame["client_id"].isin(hub.index).to_numpy() & (rng.random(n) < CGNAT_SHARE)
    gateway = np.where(
        on_hub,
        frame["client_id"].map(hub).fillna("").to_numpy(),
        frame["client_id"].map(line).to_numpy(),
    )
    country = kyc.copy()

    ringed = {c for ring in roles.rings for c in ring}
    candidates = sorted(set(home.index) - ringed - set(roles.protected) - set(hub.index))
    # A small world gets proportionally fewer travellers and privacy VPN users, never more than it has clients for.
    room = min(1.0, len(candidates) / (2 * (N_TRAVELLERS + N_PRIVACY)))
    n_travel, n_privacy = int(N_TRAVELLERS * room), int(N_PRIVACY * room)
    chosen = rng.choice(candidates, size=n_travel + n_privacy, replace=False)
    travellers_pool, privacy = (
        sorted(chosen[:n_travel]),
        frozenset(str(c) for c in chosen[n_travel:]),
    )

    ordinary = ~frame["client_id"].isin(ringed | set(privacy) | set(travellers_pool)).to_numpy()
    noise = ordinary & (rng.random(n) < BASE_FOREIGN)
    abroad = _foreign(rng, kyc)
    country = np.where(noise, abroad, country)
    gateway = np.where(
        noise,
        [
            residential(c, int(k))
            for c, k in zip(abroad, rng.integers(0, N_RESIDENTIAL, n), strict=True)
        ],
        gateway,
    )

    vpn = frame["client_id"].isin(privacy).to_numpy() & (rng.random(n) < PRIVACY_SHARE)
    country = np.where(vpn, PRIVACY_EXIT[0], country)
    gateway = np.where(vpn, PRIVACY_EXIT[1], gateway)

    exits: dict[str, frozenset[str]] = {}
    for i, ring in enumerate(roles.rings):
        exit_country = RING_EXITS[i % len(RING_EXITS)]
        share = STORY_RING_VPN if i < 2 else RING_VPN
        through = frame["client_id"].isin(ring).to_numpy() & (rng.random(n) < share)
        country = np.where(through, exit_country, country)
        gateway = np.where(through, ring_exit(exit_country, i), gateway)
        exits[ring_exit(exit_country, i)] = frozenset(ring)

    frame["ip_country"], frame["gateway_id"] = country, gateway
    frame = _ordered(
        pd.concat([frame, _controllers(frame, home, roles.rings, rng)], ignore_index=True)
    )
    frame, trips = _travel(frame, home, travellers_pool, window, rng)
    frame["session_id"] = [f"S{i:06d}" for i in range(len(frame))]
    truth = SessionTruth(
        ring_exits=exits, travellers=frozenset(trips), trips=trips, privacy_vpn=privacy
    )
    return frame[list(SESSION_COLUMNS)], truth


def _controllers(
    frame: pd.DataFrame,
    home: pd.Series,
    rings: tuple[tuple[str, ...], ...],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Sessions a ring's controller opens through the exit shortly after a member logs in from home."""
    rows = []
    for i, ring in enumerate(rings):
        exit_country = RING_EXITS[i % len(RING_EXITS)]
        at_home = frame[
            frame["client_id"].isin(ring) & (frame["ip_country"] == frame["client_id"].map(home))
        ]
        picked = at_home[rng.random(len(at_home)) < CONTROLLER_SHARE]
        lag = pd.to_timedelta(rng.uniform(*CONTROLLER_LAG_HOURS, len(picked)), unit="h")
        rows.append(
            pd.DataFrame(
                {
                    "client_id": picked["client_id"].to_numpy(),
                    "ts": (picked["ts"] + lag).to_numpy(),
                    "txn_id": None,
                    "ip_country": exit_country,
                    "gateway_id": ring_exit(exit_country, i),
                }
            )
        )
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=list(frame.columns))
    out["ts"] = pd.to_datetime(out["ts"], utc=True)
    return out


def _travel(
    frame: pd.DataFrame,
    home: pd.Series,
    travellers: list[str],
    window: tuple[pd.Timestamp, pd.Timestamp],
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, dict[str, tuple[str, str, str]]]:
    """Place each traveller's one trip; sessions inside it are abroad through a different local network each time."""
    country = frame["ip_country"].to_numpy().copy()
    gateway = frame["gateway_id"].to_numpy().copy()
    trips: dict[str, tuple[str, str, str]] = {}
    by_client = frame.groupby("client_id").indices
    for client in travellers:
        rows = by_client.get(client)
        if rows is None:
            continue
        times = frame["ts"].iloc[rows]
        span = _pick_trip(times, *window, rng)
        if span is None:
            continue
        dest = str(_foreign(rng, np.array([home[client]]))[0])
        inside = rows[((times >= span[0]) & (times <= span[1])).to_numpy()]
        country[inside] = dest
        gateway[inside] = [
            residential(dest, int(k)) for k in rng.integers(0, N_RESIDENTIAL, len(inside))
        ]
        trips[client] = (dest, span[0].isoformat(), span[1].isoformat())
    out = frame.copy()
    out["ip_country"], out["gateway_id"] = country, gateway
    return out, trips


__all__ = ["SESSION_COLUMNS", "SessionRoles", "SessionTruth", "build_sessions"]
