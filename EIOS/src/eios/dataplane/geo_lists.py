"""What a change of a published list does to this book: which countries joined or left it, and whom that touches.

An MLRO's question after an FATF plenary or an EU amendment. For every country the change names: the accounts registered
there, logging in from it, paying through its instruments, the shared exits located there, and (from BigQuery Graph) the
accounts one shared device, payment token or address away from those. A delisting is reported as carefully as a listing:
the duty to apply enhanced measures ends, the behaviour does not. The engine's own tiers are not changed by this view.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Mapping
from typing import Any

from eios.dataplane.aml_geo import GeoSnapshot, money_events
from eios.dataplane.geo_evidence import SOURCE, exposure, gateways_of
from eios.graph.store import GraphError, GraphStore
from eios.reference.editions import Change, EditionPair, changes, country_name

_LOG = logging.getLogger("eios.dataplane.geo_lists")
_TENTHS = 1000  # shares are computed in tenths of a percent so they sum to exactly 100.0


def shares(values: Mapping[str, float]) -> dict[str, float] | None:
    """Each key's share of the total in percent, to one decimal, summing to exactly 100.0 (largest remainder).

    None when the total is zero: there is nothing to attribute, which is not the same as an equal split."""
    total = sum(values.values())
    if total <= 0:
        return None
    raw = {k: v * _TENTHS / total for k, v in values.items()}
    tenths = {k: math.floor(x) for k, x in raw.items()}
    for k in sorted(raw, key=lambda k: (tenths[k] - raw[k], k))[: _TENTHS - sum(tenths.values())]:
        tenths[k] += 1
    return {k: t / 10 for k, t in tenths.items()}


def _links(store: GraphStore | None, countries: list[str]) -> dict[str, Any]:
    """Accounts one identifier away, per country, in one graph job. Countries nobody touches are not asked."""
    if not countries:
        return {"by_country": {}, "source": None, "seconds": None, "error": None}
    if store is None:
        return {"by_country": None, "source": None, "seconds": None, "error": "no graph store here"}
    try:
        result = store.run("country_links", {"countries": countries})
    except GraphError as exc:
        _LOG.warning("country links unavailable: %s", exc)
        return {"by_country": None, "source": None, "seconds": None, "error": str(exc)}
    found: dict[str, set[str]] = {c: set() for c in countries}
    for row in result.rows:
        found[row["country"]].add(row["account_id"])
    return {
        "by_country": {c: len(a) for c, a in found.items()},
        "source": result.source,
        "seconds": result.seconds,
        "error": None,
    }


def _row(change: Change, seen: Mapping[str, Any], linked: int | None) -> dict[str, Any]:
    return {
        "iso2": change.iso2,
        "name": country_name(change.iso2),
        "before": change.before,
        "after": change.after,
        "registered_accounts": seen["registered_accounts"],
        "login_accounts": seen["login_accounts"],
        "sessions": seen["sessions"],
        "payment_accounts": seen["payment_accounts"],
        "payment_volume_usd": seen["payment_volume_usd"],
        "shared_exits": seen["shared_exits"],
        "exposed_accounts": len(seen["accounts"]),
        "linked_accounts": linked,
    }


def _group(
    found: Iterable[Change], seen: Mapping[str, Mapping[str, Any]], links: Mapping[str, Any]
) -> dict[str, Any]:
    by_country = links["by_country"]
    rows = [
        _row(
            c,
            seen[c.iso2],
            # a country no account touches has nobody one hop away: that zero is certain, not measured
            0
            if not seen[c.iso2]["accounts"]
            else (by_country.get(c.iso2) if by_country is not None else None),
        )
        for c in found
    ]
    exposed: set[str] = set().union(*(seen[r["iso2"]]["accounts"] for r in rows)) if rows else set()
    return {
        "countries": rows,
        "exposed_accounts": len(exposed),
        "sessions": sum(r["sessions"] or 0 for r in rows),
        "payment_volume_usd": round(sum(r["payment_volume_usd"] for r in rows), 2),
        "session_shares": shares({r["iso2"]: r["sessions"] or 0 for r in rows}),
        "payment_shares": shares({r["iso2"]: r["payment_volume_usd"] for r in rows}),
    }


def list_change(snap: GeoSnapshot, store: GraphStore | None, pair: EditionPair) -> dict[str, Any]:
    diff = changes(pair)
    named = (*diff.added, *diff.removed, *diff.relisted)
    events, exits = money_events(snap.world, snap.tiers), gateways_of(snap)
    seen = {c.iso2: exposure(snap, c.iso2, events, exits) for c in named}
    touched = sorted(c for c, s in seen.items() if s["accounts"])
    links = _links(store, touched)
    return {
        "list_id": pair.list_id.value,
        "as_of": snap.world.config.as_of.isoformat(),
        "source": SOURCE,
        "before": _edition(pair.before),
        "after": _edition(pair.after),
        "added": _group(diff.added, seen, links),
        "removed": _group(diff.removed, seen, links),
        "relisted": _group(diff.relisted, seen, links),
        "graph": {k: links[k] for k in ("source", "seconds", "error")},
    }


def _edition(edition: Any) -> dict[str, Any]:
    return {"label": edition.label, "in_force": edition.in_force, "source": edition.source}
