"""Geography as case evidence: the overview, ranked leads, a shared exit with its ring, a corridor and a jurisdiction.

Pure functions of the geo engine's snapshot, the graph store and the reference countries, shared by the geo tools and
the cockpit routes so a screen and an answer read the same numbers. Each lens states what it can judge: a figure that
cannot be measured here is None, never zero, and a measured zero is reported as zero. Nothing reads the planted truth.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import pandas as pd

from eios.dataplane.aml_geo import GeoSnapshot, money_events
from eios.dataplane.aml_geo_sessions import (
    HUB_DEGREE,
    MIN_EXIT_SESSIONS,
    MIN_SHARED_FOREIGN,
)
from eios.graph.store import GraphError, GraphStore
from eios.reference.editions import country_name

_LOG = logging.getLogger("eios.dataplane.geo_evidence")
SOURCE = "AML engine over the seeded world (login sessions, gateways, payments)"
TOP = 5
MAX_RING = 40  # [ASSUMPTION] linked accounts listed per exit; the count covers all of them
_TIER_RANK = {"high": 2, "medium": 1}


def mismatch_pairs_of(snap: GeoSnapshot) -> list[dict[str, Any]]:
    home = snap.world.clients.set_index("client_id")["country"]
    flagged = snap.clients[snap.clients["mismatch_flag"]].copy()
    flagged["kyc_country"] = flagged["client_id"].map(home)
    pairs: list[dict[str, Any]] = []
    for (kyc, ip), group in flagged.groupby(["kyc_country", "top_foreign_ip"]):
        ranked = group.sort_values(["mismatch_p", "client_id"])
        pairs.append(
            {
                "kyc_country": kyc,
                "ip_country": ip,
                "accounts": len(group),
                "events": int(group["events"].sum()),
                "foreign_events": int(group["foreign_ip_events"].sum()),
                "volume_usd": round(float(group["volume_usd"].sum()), 2),
                "sample_accounts": ranked["client_id"].head(TOP).tolist(),
            }
        )
    return sorted(pairs, key=lambda p: (-p["accounts"], p["kyc_country"], p["ip_country"]))


def gateways_of(snap: GeoSnapshot) -> list[dict[str, Any]]:
    """Shared foreign exits with at least one flagged account: where they are, who uses them and from where."""
    lenses = snap.sessions
    if lenses is None:
        return []
    home = snap.world.clients.set_index("client_id")["country"]
    flagged = snap.clients[snap.clients["exit_flag"].fillna(False).astype(bool)]
    jumps = snap.clients.set_index("client_id")["jumps"]
    rows: list[dict[str, Any]] = []
    for g in lenses.gateways[lenses.gateways["shared_exit"]].itertuples():
        users = flagged[flagged["exit_gateway"] == g.gateway_id]
        if users.empty:
            continue
        homes = users["client_id"].map(home).value_counts()
        rows.append(
            {
                "gateway_id": g.gateway_id,
                "country": g.country,
                "accounts": len(users),
                "home_countries": [{"iso2": c, "accounts": int(n)} for c, n in homes.items()],
                "impossible_jumps": int(users["client_id"].map(jumps).fillna(0).sum()),
                "sample_accounts": sorted(users["client_id"])[:TOP],
            }
        )
    return sorted(rows, key=lambda r: (-r["accounts"], r["gateway_id"]))


def corridor_id(origin: str, destination: str) -> str:
    return f"{origin}>{destination}"


def standing(countries: Mapping[str, Any], iso2: str) -> dict[str, Any]:
    """A country's place on each published list. Absent from a list is `False`/None; absent from Basel is unrated."""
    row = next((c for c in countries.get("countries", []) if c.get("iso2") == iso2), None) or {}
    basel = row.get("basel") or None
    return {
        "iso2": iso2,
        "name": row.get("name") or country_name(iso2),
        "fatf_list": row.get("fatf_list"),
        "eu_high_risk": bool(row.get("eu_high_risk")),
        "basel_score": None if basel is None else float(basel["score"]),
        "basel_rank": None if basel is None else int(basel["rank"]),
        "basel_band": None if basel is None else basel["band"],
        "offshore_entities": row.get("entities_incorporated"),
    }


def _flag_count(clients: pd.DataFrame, column: str) -> int:
    return int(clients[column].fillna(False).astype(bool).sum())


def _lenses(snap: GeoSnapshot) -> list[dict[str, Any]]:
    c, s = snap.clients, snap.sessions
    travel = s is not None and s.travel_assessable
    return [
        {
            "lens": "shared_exit",
            "flagged": None if s is None else _flag_count(c, "exit_flag"),
            "assessable": None if s is None else int((c["sessions"].fillna(0) > 0).sum()),
        },
        {
            "lens": "impossible_travel",
            "flagged": _flag_count(c, "jump_flag") if travel else None,
            "assessable": _flag_count(c, "travel_assessable") if travel else None,
        },
        {
            "lens": "login_country",
            "flagged": _flag_count(c, "mismatch_flag"),
            "assessable": _flag_count(c, "mismatch_assessable"),
        },
        {
            "lens": "risky_corridor",
            "flagged": _flag_count(c, "corridor_flag") if snap.tiers else None,
            "assessable": _flag_count(c, "corridor_assessable") if snap.tiers else None,
        },
    ]


def _corridor_rows(snap: GeoSnapshot) -> list[dict[str, Any]]:
    """Corridors in the map's order: elevated first (high before medium), each by volume, then the rest by volume."""
    known = bool(snap.tiers)
    rows = [
        {
            "corridor_id": corridor_id(r.origin, r.destination),
            "origin": r.origin,
            "destination": r.destination,
            "tier": r.tier if known else None,
            "volume_usd": round(float(r.volume_usd), 2),
            "accounts": int(r.accounts),
            "events": int(r.events),
        }
        for r in snap.corridors.itertuples()
    ]
    return sorted(rows, key=lambda r: (-_TIER_RANK.get(r["tier"] or "", 0), -r["volume_usd"]))


def _flags_of(row: pd.Series) -> list[str]:
    names = (
        ("exit_flag", "shared_exit"),
        ("jump_flag", "impossible_travel"),
        ("mismatch_flag", "login_country"),
        ("corridor_flag", "risky_corridor"),
    )
    return [
        name for column, name in names if bool(row.get(column)) and not pd.isna(row.get(column))
    ]


def _account_rows(snap: GeoSnapshot, limit: int) -> list[dict[str, Any]]:
    home = snap.world.clients.set_index("client_id")["country"]
    top = snap.clients.sort_values(["geo_risk_score", "client_id"], ascending=[False, True])
    top = top[top["geo_risk_score"] > 0].head(limit)
    return [
        {
            "account_id": row.client_id,
            "kyc_country": str(home[row.client_id]),
            "geo_score": round(float(row.geo_risk_score), 3),
            "flags": _flags_of(pd.Series(row._asdict())),
        }
        for row in top.itertuples()
    ]


def _exit_rows(snap: GeoSnapshot) -> list[dict[str, Any]]:
    return [
        {
            "gateway_id": g["gateway_id"],
            "country": g["country"],
            "accounts": g["accounts"],
            "home_countries": len(g["home_countries"]),
            "impossible_jumps": g["impossible_jumps"],
        }
        for g in gateways_of(snap)
    ]


def _pair_rows(snap: GeoSnapshot) -> list[dict[str, Any]]:
    pairs = sorted(mismatch_pairs_of(snap), key=lambda p: (-p["accounts"], -p["volume_usd"]))
    return [{"pair_id": f"{p['kyc_country']}>{p['ip_country']}", **p} for p in pairs]


def overview(snap: GeoSnapshot) -> dict[str, Any]:
    elevated = [r for r in _corridor_rows(snap) if r["tier"] in _TIER_RANK]
    return {
        "as_of": snap.world.config.as_of.isoformat(),
        "source": SOURCE,
        "clients": len(snap.clients),
        "lenses": _lenses(snap),
        "shared_exits": len(gateways_of(snap)) if snap.sessions is not None else None,
        "hubs_suppressed": None
        if snap.sessions is None
        else int(snap.sessions.gateways["hub"].sum()),
        "elevated_corridors": len(elevated) if snap.tiers else None,
        "top_exits": _exit_rows(snap)[:TOP],
        "top_corridors": elevated[:TOP],
        "top_accounts": _account_rows(snap, TOP),
        **_hotspots(snap),
    }


def _hotspots(snap: GeoSnapshot) -> dict[str, Any]:
    """Login countries that foreign accounts keep returning to beyond chance (FDR 5%, hubs set aside under RL-4).

    Being listed is the decision. The q-values stay in the engine's table: they are mostly far below anything a
    reader would act on (around 1e-18 for Nigeria), and six equal floored values could not be told apart in an answer.
    """
    table = snap.hotspots
    if table is None:
        return {"hotspots_tested": None, "login_hotspots": []}
    found = table[table["hotspot"]]
    return {
        "hotspots_tested": len(table),
        "login_hotspots": [
            {
                "iso2": str(iso2),
                "country": country_name(str(iso2)),
                "foreign_accounts": int(r["accounts"]),
                "returning_accounts": int(r["returning"]),
            }
            for iso2, r in found.iterrows()
        ],
    }


LEAD_KINDS = ("shared_exit", "corridor", "login_country", "account")


def leads(snap: GeoSnapshot, kind: str, limit: int) -> list[dict[str, Any]]:
    if kind == "shared_exit":
        return _exit_rows(snap)[:limit]
    if kind == "corridor":
        return _corridor_rows(snap)[:limit]
    if kind == "login_country":
        return _pair_rows(snap)[:limit]
    if kind == "account":
        return _account_rows(snap, limit)
    raise ValueError(f"unknown lead kind {kind!r}")


def _ring(store: GraphStore | None, gateway_id: str) -> dict[str, Any]:
    if store is None:
        return {"source": None, "seconds": None, "linked": None, "error": "no graph store here"}
    try:
        result = store.run("exit_ring", {"gateway": gateway_id})
    except GraphError as exc:
        _LOG.warning("exit ring for %s unavailable: %s", gateway_id, exc)
        return {"source": None, "seconds": None, "linked": None, "error": str(exc)}
    linked = [r for r in result.rows if r["via"] == "identifier"]
    return {
        "source": result.source,
        "seconds": result.seconds,
        "graph_users": sum(1 for r in result.rows if r["via"] == "exit"),
        "linked_total": len(linked),
        "linked": [
            {
                "account_id": r["account_id"],
                "kyc_country": r["kyc_country"],
                "link_kind": r["kind"],
                "via_account": r["source_account"],
            }
            for r in linked[:MAX_RING]
        ],
        "error": None,
    }


def shared_exit(
    snap: GeoSnapshot, store: GraphStore | None, countries: Mapping[str, Any], gateway_id: str
) -> dict[str, Any] | None:
    """One gateway as evidence. None when the world has no such gateway; a hub says it is one and ties nobody."""
    lenses = snap.sessions
    if lenses is None or gateway_id not in set(lenses.gateways["gateway_id"]):
        return None
    g = lenses.gateways.set_index("gateway_id").loc[gateway_id]
    flagged = snap.clients[
        snap.clients["exit_flag"].fillna(False).astype(bool)
        & (snap.clients["exit_gateway"] == gateway_id)
    ]
    home = snap.world.clients.set_index("client_id")["country"]
    homes = flagged["client_id"].map(home).value_counts()
    same_country_hubs = lenses.gateways[
        (lenses.gateways["country"] == g["country"]) & lenses.gateways["hub"]
    ]
    return {
        "gateway_id": gateway_id,
        "as_of": snap.world.config.as_of.isoformat(),
        "source": SOURCE,
        "country": standing(countries, str(g["country"])),
        "hub": bool(g["hub"]),
        "shared_exit": bool(g["shared_exit"]),
        "accounts": int(g["accounts"]),
        "sessions": int(g["sessions"]),
        "foreign_accounts": int(g["foreign_accounts"]),
        "flagged_accounts": len(flagged),
        "home_countries": [{"iso2": str(c), "accounts": int(n)} for c, n in homes.items()],
        "impossible_jumps": int(flagged["jumps"].fillna(0).sum()),
        "sample_accounts": sorted(flagged["client_id"])[:TOP],
        "rule": {
            "min_shared_accounts": MIN_SHARED_FOREIGN,
            "min_sessions": MIN_EXIT_SESSIONS,
            "hub_degree": HUB_DEGREE,
        },
        "hubs_in_country": len(same_country_hubs),
        "ring": _ring(store, gateway_id) if not bool(g["hub"]) else None,
    }


def corridor(
    snap: GeoSnapshot, countries: Mapping[str, Any], origin: str, destination: str
) -> dict[str, Any] | None:
    rows = snap.corridors[
        (snap.corridors["origin"] == origin) & (snap.corridors["destination"] == destination)
    ]
    if rows.empty:
        return None
    r = rows.iloc[0]
    events = money_events(snap.world, snap.tiers)
    mine = events[(events["origin"] == origin) & (events["destination"] == destination)]
    by_account = mine.groupby("client_id")["amount"].sum().sort_values(ascending=False)
    return {
        "corridor_id": corridor_id(origin, destination),
        "as_of": snap.world.config.as_of.isoformat(),
        "source": SOURCE,
        "tier": str(r["tier"]) if snap.tiers else None,
        "volume_usd": round(float(r["volume_usd"]), 2),
        "accounts": int(r["accounts"]),
        "events": int(r["events"]),
        "deposits": int((mine["transaction_type"] == "DEPOSIT").sum()),
        "withdrawals": int((mine["transaction_type"] == "WITHDRAWAL").sum()),
        "origin": standing(countries, origin),
        "destination": standing(countries, destination),
        "top_accounts": [
            {"account_id": str(a), "volume_usd": round(float(v), 2)}
            for a, v in by_account.head(TOP).items()
        ],
    }


def exposure(
    snap: GeoSnapshot,
    iso2: str,
    events: pd.DataFrame | None = None,
    exits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """What this book does in a country: residents, logins from it, payments through it, exits located there.

    `events` and `exits` may be passed in by a caller asking about several countries, so they are computed once."""
    world, lenses = snap.world, snap.sessions
    sessions = world.geo_sessions
    here = sessions[sessions["ip_country"] == iso2] if sessions is not None else None
    events = money_events(world, snap.tiers) if events is None else events
    paying = events[(events["instrument_country"] == iso2) & (events["kyc_country"] != iso2)]
    exits = [
        g["gateway_id"]
        for g in (gateways_of(snap) if exits is None else exits)
        if g["country"] == iso2
    ]
    return {
        "registered_accounts": int((world.clients["country"] == iso2).sum()),
        "login_accounts": None if here is None else int(here["client_id"].nunique()),
        "sessions": None if here is None else len(here),
        "gateways": None if here is None else int(here["gateway_id"].nunique()),
        "payment_accounts": int(paying["client_id"].nunique()),
        "payment_volume_usd": round(float(paying["amount"].sum()), 2),
        "shared_exits": exits if lenses is not None else None,
        "accounts": _exposed(world, sessions, paying, iso2),
    }


def _exposed(
    world: Any, sessions: pd.DataFrame | None, paying: pd.DataFrame, iso2: str
) -> set[str]:
    found = set(world.clients.loc[world.clients["country"] == iso2, "client_id"])
    found |= set(paying["client_id"])
    if sessions is not None:
        found |= set(sessions.loc[sessions["ip_country"] == iso2, "client_id"])
    return found


def jurisdiction(snap: GeoSnapshot, countries: Mapping[str, Any], iso2: str) -> dict[str, Any]:
    seen = exposure(snap, iso2)
    corridors = [r for r in _corridor_rows(snap) if iso2 in (r["origin"], r["destination"])]
    return {
        "country_id": iso2,
        "as_of": snap.world.config.as_of.isoformat(),
        "source": SOURCE,
        "standing": standing(countries, iso2),
        "engine_tier": snap.tiers.get(iso2) if snap.tiers else None,
        **{k: v for k, v in seen.items() if k != "accounts"},
        "exposed_accounts": len(seen["accounts"]),
        "corridors": len(corridors),
        "corridor_volume_usd": round(sum(r["volume_usd"] for r in corridors), 2),
    }
