"""Jurisdiction risk tiers from the reference layer: the one rule every geo lens shares.

`high`: on the FATF call-for-action list. `medium`: on the FATF increased-monitoring list, or an offshore centre (many
entities incorporated there in the ICIJ leaks). Everything else is absent from the result: an unlisted country is
unrated, not proven safe, and callers treat absent as `low`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# [ASSUMPTION] incorporated entities in the leaks above which a jurisdiction counts as an offshore centre.
OFFSHORE_CENTRE_MIN_ENTITIES = 10_000


def jurisdiction_tiers(reference: Mapping[str, Any]) -> dict[str, str]:
    tiers: dict[str, str] = {}
    for country in reference.get("countries", []):
        if country.get("fatf_list") == "call_for_action":
            tiers[country["iso2"]] = "high"
        elif country.get("fatf_list") == "increased_monitoring" or (
            (country.get("entities_incorporated") or 0) >= OFFSHORE_CENTRE_MIN_ENTITIES
        ):
            tiers[country["iso2"]] = "medium"
    return tiers
