"""The address check's answer as the wire shape: what the snapshot knows about one address, and what it does not."""

from __future__ import annotations

from typing import Any

from eios.netintel.lookup import AddressReport


def address_payload(report: AddressReport) -> dict[str, Any]:
    """Codes and facts only; the words are the cockpit's. A missing country or network is null, never a guess."""
    return {
        "address": report.address,
        "version": report.version,
        "scope": report.scope,
        "country": {"iso2": report.country[0], "name": report.country[1]}
        if report.country
        else None,
        "network": (
            {"asn": report.network[0], "name": report.network[1], "domain": report.network[2]}
            if report.network
            else None
        ),
        "verdict": report.verdict,
        "lists": [{"list": m.list_name, "detail": m.detail} for m in report.matches],
        "uncovered": list(report.uncovered),
        "sources": [{"name": s.name, "as_of": s.as_of} for s in report.sources],
    }
