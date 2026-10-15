"""Read the warm tier through named queries, with the cost guards in code (docs/warm-tier.md).

`WarmStore.run` takes a catalogue query and its parameters, never SQL. BigQuery runs it after a dry run: a query over the
byte cap is refused before it spends anything, and the real run carries the same cap. The local double runs the same
query text over DuckDB tables with the same names, so offline results and warehouse results come from one definition.
An unreachable warehouse is a labelled `WarmUnavailable`, never a silent fall-back to another tier.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import duckdb

from eios.warm.queries import CATALOGUE, NamedQuery
from eios.warm.schema import table_spec

_LOG = logging.getLogger("eios.warm.store")
DEFAULT_MAX_BYTES = (
    100 * 1024 * 1024
)  # [ASSUMPTION] 100 MB per query; the tables are tiny at demo scale
_PARAM = re.compile(r":([a-z_]+)")


class WarmError(RuntimeError):
    """Base for warm-tier failures."""


class WarmUnavailable(WarmError):
    """The warehouse could not be reached or the query failed; the caller says so and shows no figure."""


class WarmQueryRefused(WarmError):
    """The query was refused before running: unknown name, missing parameter, or over the byte cap."""


@dataclass(frozen=True)
class WarmResult:
    rows: list[dict[str, Any]]
    bytes_processed: int
    source: str  # where the rows came from, for the figure's popover: backend and table
    extras: dict[str, Any] = field(default_factory=dict)


class WarmStore(Protocol):
    backend: str

    def run(self, query: str, params: Mapping[str, Any]) -> WarmResult: ...


def _lookup(query: str, params: Mapping[str, Any]) -> NamedQuery:
    named = CATALOGUE.get(query)
    if named is None:
        raise WarmQueryRefused(f"no warm query named {query!r}")
    missing = [p for p in named.params if p not in params]
    if missing:
        raise WarmQueryRefused(f"query {query!r} needs {', '.join(missing)}")
    return named


def _plain(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        k: (float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, int | bool) else v)
        for k, v in row.items()
    }


class LocalWarmStore:
    backend = "local"

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._con = connection

    def run(self, query: str, params: Mapping[str, Any]) -> WarmResult:
        named = _lookup(query, params)
        spec = table_spec(named.product)
        sql = named.sql.format(
            table=f"{spec.dataset}.{spec.table}", TS="TIMESTAMPTZ", STR="VARCHAR"
        )
        sql = _PARAM.sub(lambda m: f"${m.group(1)}", sql)
        try:
            cursor = self._con.execute(sql, {k: params[k] for k in named.params})
            names = [d[0] for d in cursor.description]
            rows = [_plain(dict(zip(names, r, strict=True))) for r in cursor.fetchall()]
        except duckdb.Error as exc:
            raise WarmUnavailable(f"the local warm tier could not answer: {exc}") from exc
        return WarmResult(rows, 0, f"warm.local:{spec.dataset}.{spec.table}")


class BigQueryWarmStore:
    backend = "bigquery"

    def __init__(
        self,
        project: str,
        *,
        client: Any = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        location: str = "us-central1",
    ) -> None:
        if client is None:
            from google.cloud import bigquery

            client = bigquery.Client(project=project, location=location)
        self._client, self._project, self._max_bytes = client, project, max_bytes

    def run(self, query: str, params: Mapping[str, Any]) -> WarmResult:
        from google.api_core.exceptions import GoogleAPICallError
        from google.cloud import bigquery

        named = _lookup(query, params)
        spec = table_spec(named.product)
        reference = f"{self._project}.{spec.dataset}.{spec.table}"
        sql = named.sql.format(table=f"`{reference}`", TS="TIMESTAMP", STR="STRING")
        sql = _PARAM.sub(lambda m: f"@{m.group(1)}", sql)
        parameters = [
            bigquery.ScalarQueryParameter(k, "STRING", str(params[k])) for k in named.params
        ]
        try:
            dry = self._client.query(
                sql,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=parameters, dry_run=True, use_query_cache=False
                ),
            )
            if dry.total_bytes_processed > self._max_bytes:
                raise WarmQueryRefused(
                    f"query {query!r} would scan {dry.total_bytes_processed} bytes, over the cap of {self._max_bytes}"
                )
            job = self._client.query(
                sql,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=parameters, maximum_bytes_billed=self._max_bytes
                ),
            )
            rows = [_plain(dict(r.items())) for r in job.result()]
        except GoogleAPICallError as exc:
            _LOG.warning("warm query %s failed", query, exc_info=True)
            raise WarmUnavailable(f"the warehouse could not answer: {type(exc).__name__}") from exc
        return WarmResult(rows, int(job.total_bytes_billed or 0), f"warm.bigquery:{reference}")
