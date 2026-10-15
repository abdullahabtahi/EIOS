"""Build the `warm_reference` dataset: jurisdictions (Overture), FATF lists, offshore precedent (ICIJ), indicators (World Bank).

The public datasets live in BigQuery's US location and the warm datasets in us-central1, and BigQuery cannot join across
locations, so the small simplified results are read out and loaded into a us-central1 dataset where corridor queries can
join the private and the reference layers. Each table is a snapshot rebuilt whole (WRITE_TRUNCATE); every row carries
its source and as-of.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from eios.reference.fatf import FATF_ROWS
from eios.reference.icij import aggregate_precedent

_LOG = logging.getLogger("eios.reference.build")
REFERENCE_DATASET = "warm_reference"
WARM_LOCATION = "us-central1"
_PUBLIC_LOCATION = "US"
OVERTURE_RELEASE = "2026-09-23"
WDI_CODES = (
    "NY.GDP.PCAP.CD",
    "NY.GDP.MKTP.CD",
    "BX.TRF.PWKR.CD.DT",
    "IT.NET.USER.ZS",
    "FS.AST.PRVT.GD.ZS",
    "BN.CAB.XOKA.GD.ZS",
)

# Country and dependency outlines (offshore places such as the British Virgin Islands are dependencies in Overture),
# simplified to 20 km, one row per country code (the largest area wins), English name preferred over the local one.
_JURISDICTIONS_SQL = """
SELECT country AS iso2,
       COALESCE((SELECT value FROM UNNEST(names.common.key_value) WHERE key = 'en'), names.primary) AS name,
       ST_ASTEXT(ST_SIMPLIFY(geometry, 20000)) AS boundary, ST_ASTEXT(ST_CENTROID(geometry)) AS centroid
FROM `bigquery-public-data.overture_maps.division_area`
WHERE subtype IN ('country', 'dependency') AND class = 'land' AND country IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY country ORDER BY ST_AREA(geometry) DESC) = 1
"""
# The latest non-null value per country and indicator; regional aggregates have no region and are left out.
_INDICATORS_SQL = """
SELECT cs.two_alpha_code AS iso2, d.indicator_code, d.indicator_name, d.year, CAST(d.value AS FLOAT64) AS value
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY country_code, indicator_code ORDER BY year DESC) AS rn
  FROM `bigquery-public-data.world_bank_wdi.indicators_data`
  WHERE indicator_code IN UNNEST(@codes) AND value IS NOT NULL
) d JOIN `bigquery-public-data.world_bank_wdi.country_summary` cs ON cs.country_code = d.country_code
WHERE d.rn = 1 AND cs.region IS NOT NULL AND cs.two_alpha_code IS NOT NULL
"""

_SCHEMAS: dict[str, list[tuple[str, str]]] = {
    "jurisdictions": [
        ("iso2", "STRING"),
        ("name", "STRING"),
        ("boundary", "GEOGRAPHY"),
        ("centroid", "GEOGRAPHY"),
        ("source", "STRING"),
        ("as_of", "STRING"),
    ],
    "jurisdiction_risk": [
        ("iso2", "STRING"),
        ("list_name", "STRING"),
        ("source", "STRING"),
        ("as_of", "STRING"),
    ],
    "offshore_precedent": [
        ("iso2", "STRING"),
        ("entities_incorporated", "INT64"),
        ("entities_linked", "INT64"),
        ("source", "STRING"),
        ("as_of", "STRING"),
    ],
    "country_indicators": [
        ("iso2", "STRING"),
        ("indicator_code", "STRING"),
        ("indicator_name", "STRING"),
        ("year", "INT64"),
        ("value", "FLOAT64"),
        ("source", "STRING"),
        ("as_of", "STRING"),
    ],
}


def _extract(client: Any, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    from google.cloud import bigquery

    config = bigquery.QueryJobConfig(
        query_parameters=params or [], maximum_bytes_billed=10 * 1024**3
    )
    return [
        dict(r) for r in client.query(sql, job_config=config, location=_PUBLIC_LOCATION).result()
    ]


def _load(client: Any, project: str, table: str, rows: list[dict[str, Any]]) -> int:
    from google.cloud import bigquery

    schema = [bigquery.SchemaField(n, t) for n, t in _SCHEMAS[table]]
    config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=schema,
    )
    client.load_table_from_json(
        rows, f"{project}.{REFERENCE_DATASET}.{table}", job_config=config, location=WARM_LOCATION
    ).result()
    return len(rows)


def build_reference(
    project: str, icij_entities_csv: Path, icij_as_of: str, *, client: Any = None
) -> dict[str, int]:
    from google.cloud import bigquery

    client = client or bigquery.Client(project=project)
    dataset = bigquery.Dataset(f"{project}.{REFERENCE_DATASET}")
    dataset.location = WARM_LOCATION
    client.create_dataset(dataset, exists_ok=True)

    overture = f"Overture Maps division_area, release {OVERTURE_RELEASE}"
    jurisdictions = [
        {**r, "source": overture, "as_of": OVERTURE_RELEASE}
        for r in _extract(client, _JURISDICTIONS_SQL)
    ]
    indicators = [
        {
            **r,
            "source": "World Bank WDI (bigquery-public-data; latest year per country)",
            "as_of": str(r.get("year", "")),
        }
        for r in _extract(
            client,
            _INDICATORS_SQL,
            [bigquery.ArrayQueryParameter("codes", "STRING", list(WDI_CODES))],
        )
    ]
    tables = {
        "jurisdictions": jurisdictions,
        "jurisdiction_risk": FATF_ROWS,
        "offshore_precedent": aggregate_precedent(icij_entities_csv, as_of=icij_as_of),
        "country_indicators": indicators,
    }
    summary = {name: _load(client, project, name, rows) for name, rows in tables.items()}
    _LOG.info("reference layer built: %s", summary)
    return summary
