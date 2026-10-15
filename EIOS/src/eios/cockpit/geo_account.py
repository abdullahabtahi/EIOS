"""One account's geography, as evidence for the case: where it registered, where it logs in from, through which
gateways, any jump no flight could make, the countries its money crosses, what each lens concluded, and the accounts it
is linked to in the graph.

Pure over the geo snapshot, except the neighbourhood, which comes from the graph store (BigQuery Graph when configured,
else the local double) and names its source; a graph outage leaves that section empty with the reason and the rest of
the evidence intact. Nothing here reads the planted truth.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from eios.dataplane.aml_geo import GeoSnapshot
from eios.graph.store import GraphError, GraphStore

_LOG = logging.getLogger("eios.cockpit.geo_account")
SOURCE = "AML engine over the seeded world (login sessions, gateways, payments)"
_MAX_JUMP_EXAMPLES = 3
_MAX_NEIGHBOURS = 40
_MONEY = ("COMPLETED", "PENDING")


def _flag(row: pd.Series, column: str) -> bool:
    value = row.get(column)
    return bool(value) if value is not None and not pd.isna(value) else False


def _logins(snap: GeoSnapshot, account: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sessions = snap.world.geo_sessions
    if sessions is None:
        return [], []
    mine = sessions[sessions["client_id"] == account]
    countries = [
        {"iso2": c, "sessions": int(n)} for c, n in mine["ip_country"].value_counts().items()
    ]
    lenses = snap.sessions
    table = lenses.gateways.set_index("gateway_id") if lenses is not None else pd.DataFrame()
    gateways = []
    for gateway_id, n in mine["gateway_id"].value_counts().items():
        info = table.loc[gateway_id] if gateway_id in table.index else None
        gateways.append(
            {
                "gateway_id": gateway_id,
                "country": gateway_id[3:5],
                "sessions": int(n),
                "accounts": None if info is None else int(info["accounts"]),
                "hub": None if info is None else bool(info["hub"]),
                "shared_exit": None if info is None else bool(info["shared_exit"]),
            }
        )
    return countries, gateways


def _jumps(snap: GeoSnapshot, account: str) -> dict[str, Any] | None:
    lenses = snap.sessions
    if lenses is None or not lenses.travel_assessable:
        return None  # no country positions: not assessable, which is not the same as none
    mine = lenses.jumps[lenses.jumps["client_id"] == account].sort_values("hours")
    return {
        "count": int((~mine["via_hub"]).sum()),
        "via_hub": int(mine["via_hub"].sum()),
        "examples": [
            {
                "from": r.from_country,
                "to": r.to_country,
                "hours": float(r.hours),
                "km": int(r.km),
                "at": pd.Timestamp(r.to_ts).isoformat(),
            }
            for r in mine[~mine["via_hub"]].head(_MAX_JUMP_EXAMPLES).itertuples()
        ],
    }


def _payments(snap: GeoSnapshot, account: str, kyc: str) -> list[dict[str, Any]]:
    flows = snap.world.geo_flows
    if flows is None:
        return []
    txn = snap.world.transactions[["txn_id", "transaction_type", "amount", "status"]]
    mine = flows[flows["client_id"] == account].merge(txn, on="txn_id")
    mine = mine[mine["status"].isin(_MONEY) & (mine["instrument_country"] != kyc)]
    rows = []
    for (country, kind), group in mine.groupby(["instrument_country", "transaction_type"]):
        rows.append(
            {
                "iso2": country,
                "direction": "in" if kind == "DEPOSIT" else "out",
                "events": len(group),
                "volume_usd": round(float(group["amount"].sum()), 2),
                "tier": snap.tiers.get(country) if snap.tiers else None,
            }
        )
    return sorted(rows, key=lambda r: -r["volume_usd"])


def _lenses(row: pd.Series) -> dict[str, Any]:
    return {
        "mismatch": {
            "flag": _flag(row, "mismatch_flag"),
            "assessable": _flag(row, "mismatch_assessable"),
            "foreign_events": int(row["foreign_ip_events"]),
            "events": int(row["events"]),
        },
        "shared_exit": {
            "flag": _flag(row, "exit_flag"),
            "gateway": None if pd.isna(row.get("exit_gateway")) else row.get("exit_gateway"),
            "sessions": int(row.get("exit_sessions") or 0),
        },
        "travel": {"flag": _flag(row, "jump_flag"), "assessable": _flag(row, "travel_assessable")},
        "corridor": {
            "flag": _flag(row, "corridor_flag"),
            "assessable": _flag(row, "corridor_assessable"),
        },
    }


def _neighbourhood(store: GraphStore | None, account: str) -> dict[str, Any]:
    if store is None:
        return {"source": None, "rows": None, "error": "no graph store on this plane"}
    try:
        result = store.run("account_neighbourhood", {"account": account})
    except GraphError as exc:
        _LOG.warning("graph neighbourhood for %s unavailable: %s", account, exc)
        return {"source": None, "rows": None, "error": str(exc)}
    return {
        "source": result.source,
        "seconds": result.seconds,
        "total": len(result.rows),
        "rows": result.rows[:_MAX_NEIGHBOURS],
        "error": None,
    }


def account_payload(
    snap: GeoSnapshot, account: str, store: GraphStore | None
) -> dict[str, Any] | None:
    """The account's geography, or None when the world holds no such account."""
    table = snap.clients.set_index("client_id")
    if account not in table.index:
        return None
    row = table.loc[account]
    kyc = str(snap.world.clients.set_index("client_id").loc[account, "country"])
    countries, gateways = _logins(snap, account)
    return {
        "account_id": account,
        "kyc_country": kyc,
        "source": SOURCE,
        "as_of": snap.world.config.as_of.isoformat(),
        "sessions": int(row.get("sessions") or 0),
        "login_countries": countries,
        "gateways": gateways,
        "jumps": _jumps(snap, account),
        "payments": _payments(snap, account, kyc),
        "lenses": _lenses(row),
        "geo_score": round(float(row["geo_risk_score"]), 3),
        "neighbourhood": _neighbourhood(store, account),
    }
