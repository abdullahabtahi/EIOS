"""Read the warm tier through named queries, with the cost guards in code (docs/warm-tier.md).

`WarmStore.run` takes a catalogue query and its parameters, never SQL. BigQuery runs it with `maximum_bytes_billed` set: a
query over the cap fails server-side without being charged, so there is no separate dry run (it cost a round trip, about
a third of the query time, to learn what the cap already enforces). The local double runs the same
query text over DuckDB tables with the same names, so offline results and warehouse results come from one definition.
An unreachable warehouse is a labelled `WarmUnavailable`, never a silent fall-back to another tier.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol

import duckdb

from eios.warm.queries import CATALOGUE, NamedQuery
from eios.warm.schema import table_spec

_LOG = logging.getLogger("eios.warm.store")
DEFAULT_MAX_BYTES = (
    100 * 1024 * 1024
)  # [ASSUMPTION] 100 MB per query; the tables are tiny at demo scale
_PARAM = re.compile(r":([a-z_]+)")
LABEL_MAX_LEN = 63  # BigQuery's limit for a label key or value
# The ASCII subset of what BigQuery accepts: lowercase letters, digits, underscore and dash; a key starts with a letter.
_LABEL_KEY = re.compile(rf"[a-z][a-z0-9_-]{{0,{LABEL_MAX_LEN - 1}}}")
_LABEL_VALUE = re.compile(
    rf"[a-z0-9_-]{{1,{LABEL_MAX_LEN}}}"
)  # an empty value is left out, not sent
BASE_LABELS: Mapping[str, str] = MappingProxyType({"app": "eios", "component": "warm-tier"})
RESERVED_LABELS = frozenset({*BASE_LABELS, "query"})


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


def is_valid_label(key: str, value: str) -> bool:
    return bool(_LABEL_KEY.fullmatch(key) and _LABEL_VALUE.fullmatch(value))


def _valid_labels(labels: Mapping[str, str]) -> dict[str, str]:
    """The caller's labels BigQuery would accept. Empty values are left out quietly (an unset environment); reserved
    keys and invalid labels are dropped with a warning, so a bad label can never fail a query."""
    reserved = sorted(set(labels) & RESERVED_LABELS)
    kept = {
        k: v
        for k, v in labels.items()
        if k not in RESERVED_LABELS and (v == "" or is_valid_label(k, v))
    }
    invalid = sorted(set(labels) - set(kept) - set(reserved))
    if reserved or invalid:
        _LOG.warning(
            "warm query labels dropped: reserved %s, not valid for BigQuery %s", reserved, invalid
        )
    return {k: v for k, v in kept.items() if v != ""}


class BigQueryWarmStore:
    backend = "bigquery"

    def __init__(
        self,
        project: str,
        *,
        client: Any = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        location: str = "us-central1",
        labels: Mapping[str, str] | None = None,
    ) -> None:
        if client is None:
            from google.cloud import bigquery

            client = bigquery.Client(project=project, location=location)
        self._client, self._project, self._max_bytes = client, project, max_bytes
        self._labels = {**_valid_labels(labels or {}), **BASE_LABELS}

    def run(self, query: str, params: Mapping[str, Any]) -> WarmResult:
        from google.api_core.exceptions import BadRequest, GoogleAPICallError
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
            job = self._client.query(
                sql,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=parameters,
                    maximum_bytes_billed=self._max_bytes,
                    labels={
                        **self._labels,
                        "query": named.name,
                    },  # spend per named query: INFORMATION_SCHEMA.JOBS
                ),
            )
            rows = [_plain(dict(r.items())) for r in job.result()]
        except BadRequest as exc:
            # BigQuery enforces the cap itself: a query that would bill more fails without being charged.
            if "bytes billed" in str(exc):
                raise WarmQueryRefused(
                    f"query {query!r} would bill more than the cap of {self._max_bytes} bytes"
                ) from exc
            _LOG.warning("warm query %s was rejected", query, exc_info=True)
            raise WarmUnavailable(
                f"the warehouse rejected the query: {type(exc).__name__}"
            ) from exc
        except GoogleAPICallError as exc:
            _LOG.warning("warm query %s failed", query, exc_info=True)
            raise WarmUnavailable(f"the warehouse could not answer: {type(exc).__name__}") from exc
        return WarmResult(rows, int(job.total_bytes_billed or 0), f"warm.bigquery:{reference}")
