"""One account's geography as the geo capability returns it: the N2 evidence, each lens's finding and the rule it applied.

The evidence is the cockpit's own (`cockpit/geo_account.py`), so the map's account panel and the answer agree. What is
added here is what a "why" question needs: the thresholds the lenses apply, and whether each lens could judge at all.
"""

from __future__ import annotations

from typing import Any

from eios.cockpit.geo_account import account_payload
from eios.dataplane.aml_geo import ALPHA, GeoSnapshot
from eios.dataplane.aml_geo_sessions import MAX_SPEED_KMH, MIN_EXIT_SESSIONS, MIN_JUMP_KM, MIN_JUMPS
from eios.graph.store import GraphStore
from eios.ontology.omcp.port.geo_models import MapKind, MapTarget

MAX_TARGET_NEIGHBOURS = (
    6  # [ASSUMPTION] linked accounts offered to the map; the evidence lists more
)


def _findings(lenses: dict[str, Any], travel_known: bool) -> list[dict[str, Any]]:
    return [
        {"lens": "shared_exit", "flag": lenses["shared_exit"]["flag"], "assessable": None},
        {
            "lens": "impossible_travel",
            "flag": lenses["travel"]["flag"],
            "assessable": lenses["travel"]["assessable"] if travel_known else False,
        },
        {
            "lens": "login_country",
            "flag": lenses["mismatch"]["flag"],
            "assessable": lenses["mismatch"]["assessable"],
        },
        {
            "lens": "risky_corridor",
            "flag": lenses["corridor"]["flag"],
            "assessable": lenses["corridor"]["assessable"],
        },
    ]


def _jumps(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    return {
        "count": raw["count"],
        "via_hub": raw["via_hub"],
        "examples": [
            {
                "from_country": j["from"],
                "to_country": j["to"],
                "hours": j["hours"],
                "km": j["km"],
                "at": j["at"],
            }
            for j in raw["examples"]
        ],
    }


def _benign(p: dict[str, Any], exit_flagged: bool) -> list[dict[str, str]]:
    """The innocent explanations this account's own data supports (false-lead control). Each is read from a field of
    the evidence; none carries a number, so none adds a figure the assembler would have to trace."""
    found: list[dict[str, str]] = []
    hubs = [g["gateway_id"] for g in p["gateways"] if g.get("hub")]
    if hubs:
        found.append(
            {
                "code": "shared_infrastructure",
                "reading": f"Sessions through {', '.join(hubs)} pass a gateway that many unrelated accounts use "
                "(a carrier NAT or a commercial VPN); it is set aside under RL-4 and ties the account to no one.",
            }
        )
    jumps = p.get("jumps")
    if jumps and jumps["via_hub"]:
        found.append(
            {
                "code": "hub_position",
                "reading": "Some of the jumps start or end at a hub, whose location is the gateway's, not the user's.",
            }
        )
    foreign = {c["iso2"] for c in p["login_countries"] if c["iso2"] != p["kyc_country"]}
    if len(foreign) == 1 and not exit_flagged:
        found.append(
            {
                "code": "single_country_abroad",
                "reading": f"Logins abroad come from {next(iter(foreign))} only, through no shared exit: "
                "consistent with travel or living abroad.",
            }
        )
    if not p["payments"]:
        found.append(
            {
                "code": "no_money_abroad",
                "reading": "No money moved across a border: the geography is in the logins alone.",
            }
        )
    return found


def _neighbourhood(raw: dict[str, Any]) -> dict[str, Any]:
    rows = raw.get("rows")
    return {
        "source": raw.get("source"),
        "seconds": raw.get("seconds"),
        "total": raw.get("total"),
        "rows": None
        if rows is None
        else [
            {
                "via": r["via"],
                "link_id": r["link"],
                "detail": r["detail"],
                "account_id": r["account_id"],
                "kyc_country": r["kyc_country"],
            }
            for r in rows
        ],
        "error": raw.get("error"),
    }


def _targets(p: dict[str, Any], exit_gateway: str | None) -> list[MapTarget]:
    found = [MapTarget(kind=MapKind.ACCOUNT, target_id=p["account_id"])]
    if exit_gateway:
        found.append(MapTarget(kind=MapKind.GATEWAY, target_id=exit_gateway))
    found += [
        MapTarget(kind=MapKind.COUNTRY, target_id=c)
        for c in dict.fromkeys([p["kyc_country"], *(x["iso2"] for x in p["login_countries"])])
    ]
    neighbours = dict.fromkeys(r["account_id"] for r in p["neighbourhood"].get("rows") or [])
    found += [
        MapTarget(kind=MapKind.ACCOUNT, target_id=a)
        for a in list(neighbours)[:MAX_TARGET_NEIGHBOURS]
    ]
    return found


def account_evidence(
    snap: GeoSnapshot, store: GraphStore | None, account_id: str
) -> dict[str, Any] | None:
    """The fields of `GeoAccountEvidence` for one account, or None when the world holds no such account."""
    p = account_payload(snap, account_id, store)
    if p is None:
        return None
    lenses = p["lenses"]
    exit_gateway = lenses["shared_exit"]["gateway"] if lenses["shared_exit"]["flag"] else None
    return {
        "account_id": p["account_id"],
        "kyc_country": p["kyc_country"],
        "sessions": p["sessions"],
        "login_countries": p["login_countries"],
        "login_country_count": len(p["login_countries"]),
        "gateways": p["gateways"],
        "gateway_count": len(p["gateways"]),
        "foreign_logins": sum(
            c["sessions"] for c in p["login_countries"] if c["iso2"] != p["kyc_country"]
        ),
        "exit_gateway_id": exit_gateway,
        "exit_sessions": lenses["shared_exit"]["sessions"],
        "jumps": _jumps(p["jumps"]),
        "payments": p["payments"],
        "findings": _findings(lenses, p["jumps"] is not None),
        "benign_readings": _benign(p, exit_gateway is not None),
        "rule": {
            "min_exit_sessions": MIN_EXIT_SESSIONS,
            "min_jumps": MIN_JUMPS,
            "max_speed_kmh": MAX_SPEED_KMH,
            "min_jump_km": MIN_JUMP_KM,
            "login_alpha": ALPHA,
        },
        "geo_score": p["geo_score"],
        "neighbourhood": _neighbourhood(p["neighbourhood"]),
        "map_targets": _targets(p, exit_gateway),
    }
