"""ICIJ Offshore Leaks, entities only (policy D-1: no natural persons), counted per country.

`entities_incorporated`: entities whose jurisdiction of incorporation is the country.
`entities_linked`: entities with an address or link in the country (the file's `country_codes`).
Entities whose jurisdiction cannot be resolved to a country are kept under `UNMAPPED`, never dropped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from eios.reference.iso import to_iso2

SOURCE = "ICIJ Offshore Leaks Database (entities, node file)"
UNMAPPED = "UNMAPPED"


def aggregate_precedent(entities_csv: Path, *, as_of: str) -> list[dict[str, Any]]:
    con = duckdb.connect()
    path = str(entities_csv)
    incorporated = con.execute(
        "SELECT coalesce(jurisdiction, '') AS code, count(*) AS n "
        "FROM read_csv(?, header=true, ignore_errors=true, all_varchar=true) GROUP BY 1",
        [path],
    ).fetchall()
    linked = con.execute(
        "WITH x AS (SELECT unnest(string_split(country_codes, ';')) AS code "
        "FROM read_csv(?, header=true, ignore_errors=true, all_varchar=true) WHERE country_codes IS NOT NULL) "
        "SELECT code, count(*) AS n FROM x GROUP BY 1",
        [path],
    ).fetchall()
    counts: dict[str, dict[str, int]] = {}
    for key, pairs in (("entities_incorporated", incorporated), ("entities_linked", linked)):
        for code, n in pairs:
            iso2 = to_iso2(code) or UNMAPPED
            bucket = counts.setdefault(iso2, {"entities_incorporated": 0, "entities_linked": 0})
            bucket[key] += int(n)
    return [
        {"iso2": iso2, **c, "source": SOURCE, "as_of": as_of}
        for iso2, c in sorted(counts.items(), key=lambda kv: -kv[1]["entities_incorporated"])
    ]
