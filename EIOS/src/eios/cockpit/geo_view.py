"""The geo engine's results shaped for the map: corridors, flagged IP-versus-KYC country pairs and tier exposure.

Pure: a snapshot in, a JSON-ready dict out. The planted truth and the evaluation against it never reach this payload, and a corridor whose tier is
unknown (no reference layer) carries `null`, never `low`.
"""

from __future__ import annotations

from typing import Any

from eios.dataplane.aml_geo import GeoSnapshot
from eios.dataplane.geo_evidence import corridor_breakdown, gateways_of, mismatch_pairs_of

SOURCE = (
    "AML engine over the seeded world (IP country, payment-instrument country, transaction amounts)"
)


def _corridors(snap: GeoSnapshot) -> list[dict[str, Any]]:
    known = bool(snap.tiers)
    detail = corridor_breakdown(snap)
    return [
        {
            "origin": r.origin,
            "destination": r.destination,
            "volume_usd": round(float(r.volume_usd), 2),
            "accounts": int(r.accounts),
            "events": int(r.events),
            "tier": r.tier if known else None,
            **detail[(r.origin, r.destination)],
        }
        for r in snap.corridors.itertuples()
    ]


def _hubs_suppressed(snap: GeoSnapshot) -> int | None:
    return None if snap.sessions is None else int(snap.sessions.gateways["hub"].sum())


def _coverage(snap: GeoSnapshot) -> dict[str, int | None]:
    """How many clients each lens can judge at all. Computed from the engine's own statistics, never from the truth."""
    clients = snap.clients
    return {
        "clients": len(clients),
        "mismatch_assessable": int(clients["mismatch_assessable"].sum()),
        "corridor_assessable": int(clients["corridor_assessable"].sum()) if snap.tiers else None,
    }


def flows_payload(snap: GeoSnapshot) -> dict[str, Any]:
    corridors = _corridors(snap)
    known = bool(snap.tiers)
    exposure: dict[str, float] | None = None
    if known:
        exposure = {"low": 0.0, "medium": 0.0, "high": 0.0}
        for row in corridors:
            exposure[row["tier"]] += row["volume_usd"]
        exposure = {tier: round(volume, 2) for tier, volume in exposure.items()}
    return {
        "source": SOURCE,
        "as_of": snap.world.config.as_of.isoformat(),
        "tiers_known": known,
        "corridors": corridors,
        "mismatch_pairs": mismatch_pairs_of(snap),
        "exposure": exposure,
        "coverage": _coverage(snap),
        "gateways": gateways_of(snap),
        "hubs_suppressed": _hubs_suppressed(snap),
    }
