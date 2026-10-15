"""Where a batch of rows goes: the BigQuery warm tier, or a DuckDB double with the same tables for offline work.

Both are idempotent per batch id: loading a batch twice leaves one copy. BigQuery gets it from a deterministic load job
id (a second job with the same id is refused, which means the batch is already there); the local double checks the
batch id. Both create tables from the same generated specs, so what a test sees is what the warehouse holds.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

import duckdb

from eios.contracts.base import DataProductEnum
from eios.warm.schema import TableSpec, all_specs, dlq_spec, table_spec

_LOG = logging.getLogger("eios.warm.sink")
_DUCKDB_TYPES = {
    "STRING": "VARCHAR",
    "INT64": "BIGINT",
    "FLOAT64": "DOUBLE",
    "BOOL": "BOOLEAN",
    "TIMESTAMP": "TIMESTAMPTZ",
    "DATE": "DATE",
}


class WarmSink(Protocol):
    def load(self, product: DataProductEnum, rows: list[dict[str, Any]], *, batch_id: str) -> int:
        """Append the rows of one batch; returns how many were written (0 if the batch was already there)."""
        ...

    def quarantine(self, rows: list[dict[str, Any]], *, batch_id: str) -> int: ...


def _column(field: dict[str, str]) -> str:
    sql_type = _DUCKDB_TYPES[field["type"]]
    return (
        f'"{field["name"]}" {sql_type}[]'
        if field["mode"] == "REPEATED"
        else f'"{field["name"]}" {sql_type}'
    )


class LocalWarmSink:
    """DuckDB tables named like the warehouse's (`warm_aml.transactions_aml`). `connection` is what a local store reads."""

    def __init__(self, connection: duckdb.DuckDBPyConnection | None = None) -> None:
        self.connection = connection or duckdb.connect(":memory:")
        self.connection.execute("SET TimeZone='UTC'")  # BigQuery's TIMESTAMP and DATE(...) are UTC
        for spec in (
            all_specs()
        ):  # every table exists from the start, so a query over no data is empty, not an error
            self._ensure(spec)

    def _ensure(self, spec: TableSpec) -> str:
        name = f"{spec.dataset}.{spec.table}"
        self.connection.execute(f"CREATE SCHEMA IF NOT EXISTS {spec.dataset}")
        columns = ", ".join(_column(f) for f in spec.fields)
        self.connection.execute(f"CREATE TABLE IF NOT EXISTS {name} ({columns})")
        return name

    def _append(self, spec: TableSpec, rows: list[dict[str, Any]], batch_id: str) -> int:
        if not rows:
            return 0
        name = self._ensure(spec)
        if self.connection.execute(
            f"SELECT 1 FROM {name} WHERE _batch_id = ? LIMIT 1",  # noqa: S608 - the table name comes from our generated spec
            [batch_id],
        ).fetchone():
            return 0
        names = [f["name"] for f in spec.fields]
        quoted = ", ".join(f'"{n}"' for n in names)
        marks = ", ".join("?" for _ in names)
        self.connection.executemany(
            f"INSERT INTO {name} ({quoted}) VALUES ({marks})",  # noqa: S608 - names come from our generated spec
            [[row.get(n) for n in names] for row in rows],
        )
        return len(rows)

    def load(self, product: DataProductEnum, rows: list[dict[str, Any]], *, batch_id: str) -> int:
        return self._append(table_spec(product), rows, batch_id)

    def quarantine(self, rows: list[dict[str, Any]], *, batch_id: str) -> int:
        return self._append(dlq_spec(), rows, batch_id)


class BigQueryWarmSink:
    """Load jobs from newline-delimited JSON with the generated schema. No streaming inserts, no autodetect."""

    def __init__(self, project: str, *, client: Any = None, location: str = "us-central1") -> None:
        if client is None:
            from google.cloud import bigquery

            client = bigquery.Client(project=project, location=location)
        self._client, self._project, self._location = client, project, location

    def _load(self, spec: TableSpec, rows: list[dict[str, Any]], batch_id: str) -> int:
        from google.api_core.exceptions import Conflict
        from google.cloud import bigquery

        if not rows:
            return 0
        schema = [bigquery.SchemaField(f["name"], f["type"], mode=f["mode"]) for f in spec.fields]
        config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=schema,
        )
        job_id = f"load_{spec.table}_{batch_id}"
        try:
            job = self._client.load_table_from_json(
                rows,
                f"{self._project}.{spec.dataset}.{spec.table}",
                job_config=config,
                job_id=job_id,
                location=self._location,
            )
            job.result()
        except Conflict:
            _LOG.info("batch %s is already loaded into %s.%s", batch_id, spec.dataset, spec.table)
            return 0
        return len(rows)

    def load(self, product: DataProductEnum, rows: list[dict[str, Any]], *, batch_id: str) -> int:
        return self._load(table_spec(product), rows, batch_id)

    def quarantine(self, rows: list[dict[str, Any]], *, batch_id: str) -> int:
        return self._load(dlq_spec(), rows, batch_id)
