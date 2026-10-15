"""The geo engine's results shaped for the map: corridors, flagged IP-versus-KYC country pairs and tier exposure.

Pure: a snapshot in, a JSON-ready dict out. The planted truth and the evaluation against it never reach this payload, and a corridor whose tier is
unknown (no reference layer) carries `null`, never `low`.
"""

from __future__ import annotations

from typing import Any

from eios.dataplane.aml_geo import GeoSnapshot

SOURCE = (
    "AML engine over the seeded world (IP country, payment-instrument country, transaction amounts)"
)
_SAMPLE_ACCOUNTS = 5


def _corridors(snap: GeoSnapshot) -> list[dict[str, Any]]:
    known = bool(snap.tiers)
    return [
        {
            "origin": r.origin,
            "destination": r.destination,
            "volume_usd": round(float(r.volume_usd), 2),
            "accounts": int(r.accounts),
            "events": int(r.events),
            "tier": r.tier if known else None,
        }
        for r in snap.corridors.itertuples()
    ]


def _mismatch_pairs(snap: GeoSnapshot) -> list[dict[str, Any]]:
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
                "sample_accounts": ranked["client_id"].head(_SAMPLE_ACCOUNTS).tolist(),
            }
        )
    return sorted(pairs, key=lambda p: (-p["accounts"], p["kyc_country"], p["ip_country"]))


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
        "mismatch_pairs": _mismatch_pairs(snap),
        "exposure": exposure,
    }
