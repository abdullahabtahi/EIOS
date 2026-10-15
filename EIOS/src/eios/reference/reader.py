"""Read the `warm_reference` snapshot for the cockpit: one query, cached, with source and as-of per layer.

The tables are rebuilt whole by `python -m eios.reference build`, so a process reads them once. An empty or missing
warehouse is `ReferenceUnavailable`, never an empty map.
"""

from __future__ import annotations

import json
import os
import re
import threading
from typing import Any

from eios.reference.build import REFERENCE_DATASET

_MAX_BYTES_BILLED = 1024**3
_PROJECT_ID = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]")

# The project id is operator config, validated below against the GCP id format; BigQuery cannot bind identifiers.
_SQL = f"""
WITH ind AS (
  SELECT iso2, ARRAY_AGG(STRUCT(indicator_code AS code, indicator_name AS name, year, value) ORDER BY indicator_code) AS indicators
  FROM `{{project}}.{REFERENCE_DATASET}.country_indicators` GROUP BY iso2
)
SELECT j.iso2, j.name, ST_ASGEOJSON(j.boundary) AS boundary, ST_X(j.centroid) AS lng, ST_Y(j.centroid) AS lat,
       r.list_name AS fatf_list, p.entities_incorporated, p.entities_linked,
       j.as_of AS boundary_as_of, r.as_of AS fatf_as_of, p.as_of AS precedent_as_of, ind.indicators
FROM `{{project}}.{REFERENCE_DATASET}.jurisdictions` j
LEFT JOIN `{{project}}.{REFERENCE_DATASET}.jurisdiction_risk` r USING (iso2)
LEFT JOIN `{{project}}.{REFERENCE_DATASET}.offshore_precedent` p USING (iso2)
LEFT JOIN ind USING (iso2)
ORDER BY j.iso2
"""  # noqa: S608

_SOURCES = {
    "boundaries": ("Overture Maps division_area", "boundary_as_of"),
    "fatf": (
        "FATF plenary statement, June 2026 (secondary summary; verify against fatf-gafi.org)",
        "fatf_as_of",
    ),
    "offshore_precedent": ("ICIJ Offshore Leaks Database (entities)", "precedent_as_of"),
    "indicators": ("World Bank WDI (latest year per country)", None),
}


class ReferenceUnavailable(RuntimeError):
    """The reference layer is not configured or holds no rows."""


class ReferenceReader:
    def __init__(self, project: str, *, client: Any = None) -> None:
        if not _PROJECT_ID.fullmatch(project):
            raise ValueError(f"not a GCP project id: {project!r}")
        self._project, self._client = project, client
        self._lock = threading.Lock()
        self._cached: dict[str, Any] | None = None

    def _rows(self) -> list[dict[str, Any]]:
        from google.cloud import bigquery

        client = self._client or bigquery.Client(project=self._project)
        config = bigquery.QueryJobConfig(maximum_bytes_billed=_MAX_BYTES_BILLED)
        job = client.query(
            _SQL.format(project=self._project), job_config=config, location="us-central1"
        )
        return [dict(r) for r in job.result()]

    def world(self) -> dict[str, Any]:
        with self._lock:
            if self._cached is None:
                rows = self._rows()
                if not rows:
                    raise ReferenceUnavailable("warm_reference holds no jurisdictions")
                self._cached = _payload(rows)
            return self._cached


def _payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    countries = [
        {
            "iso2": r["iso2"],
            "name": r["name"],
            "boundary": json.loads(r["boundary"]),
            "position": [r["lng"], r["lat"]],
            "fatf_list": r["fatf_list"],
            "entities_incorporated": r["entities_incorporated"],
            "entities_linked": r["entities_linked"],
            "indicators": [dict(i) for i in (r["indicators"] or [])],
        }
        for r in rows
    ]
    sources = {
        layer: {
            "source": source,
            "as_of": next((r[column] for r in rows if column and r.get(column)), None),
        }
        for layer, (source, column) in _SOURCES.items()
    }
    return {"countries": countries, "sources": sources}


def reader_from_env() -> ReferenceReader | None:
    """A reader only when the warehouse is the BigQuery warm tier (the same switch as `eios.warm.config`)."""
    project = os.getenv("EIOS_WARM_PROJECT")
    if os.getenv("EIOS_WARM_BACKEND") != "bigquery" or not project:
        return None
    return ReferenceReader(project)
