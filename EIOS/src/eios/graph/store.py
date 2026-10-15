"""Run the named graph queries: BigQuery Graph (GQL through GRAPH_TABLE) or a local DuckDB double.

`GraphStore.run` takes a catalogue name and parameters, never SQL. BigQuery runs GQL only on an Enterprise reservation,
so each graph job names the reservation itself; nothing else in the project changes how it is billed. Before answering,
the BigQuery store checks that the warehouse tables were built from the world the cockpit serves; tables from another
world are refused, not used. An unreachable warehouse is a labelled `GraphUnavailable`, never a silent fall-back.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import duckdb

from eios.graph.queries import CATALOGUE, GraphQuery, compose
from eios.graph.tables import GRAPH_DATASET, GRAPH_NAME, GraphTables

_LOG = logging.getLogger("eios.graph.store")
_PARAM = re.compile(r"@([a-z_]+)")
_PROJECT = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
META_TABLE = "_meta"


class GraphError(RuntimeError):
    """Base for graph failures."""


class GraphUnavailable(GraphError):
    """The graph could not answer: warehouse unreachable, tables stale, or the query failed."""


class GraphQueryRefused(GraphError):
    """Unknown query name or a missing parameter; nothing ran."""


@dataclass(frozen=True)
class GraphResult:
    rows: list[dict[str, Any]]
    source: str  # where the rows came from, for the figure's popover
    seconds: float
    slot_ms: int | None = None


class GraphStore(Protocol):
    backend: str

    def run(self, query: str, params: Mapping[str, Any]) -> GraphResult: ...


def _lookup(query: str, params: Mapping[str, Any]) -> GraphQuery:
    named = CATALOGUE.get(query)
    if named is None:
        raise GraphQueryRefused(f"no graph query named {query!r}")
    missing = [p for p in named.params if p not in params]
    if missing:
        raise GraphQueryRefused(f"{query} needs {', '.join(missing)}")
    return named


class LocalGraphStore:
    """The same queries as plain joins over the same tables in DuckDB: offline, CI and a laptop need no cloud."""

    backend = "local"

    def __init__(self, tables: GraphTables) -> None:
        self._tables = tables
        self._lock = threading.Lock()
        self._con = duckdb.connect()
        for name, frame in tables.frames.items():
            self._con.register(name, frame)

    def run(self, query: str, params: Mapping[str, Any]) -> GraphResult:
        named = _lookup(query, params)
        sql = _PARAM.sub(r"$\1", compose(named, graph=None))
        started = time.perf_counter()
        with self._lock:  # one DuckDB connection, used from request threads
            cur = self._con.execute(sql, {p: params[p] for p in named.params})
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
        return GraphResult(
            rows, f"graph.local:{GRAPH_NAME}", round(time.perf_counter() - started, 4)
        )


class BigQueryGraphStore:
    """GQL over the property graph `warm_graph.aml_geo`, each job on the named Enterprise reservation."""

    backend = "bigquery"

    def __init__(
        self,
        project: str,
        reservation: str,
        fingerprint: str,
        client: Any | None = None,
        dataset: str = GRAPH_DATASET,
    ) -> None:
        if not _PROJECT.match(project):
            raise ValueError(f"not a project id: {project!r}")
        self._project, self._dataset, self._reservation, self._fingerprint = (
            project,
            dataset,
            reservation,
            fingerprint,
        )
        self._client = client
        self._checked = False
        self._lock = threading.Lock()

    @property
    def graph(self) -> str:
        return f"`{self._project}.{self._dataset}.{GRAPH_NAME}`"

    def _bq(self) -> Any:
        if self._client is None:
            from google.cloud import bigquery

            self._client = bigquery.Client(project=self._project)
        return self._client

    def _check_fresh(self) -> None:
        """The warehouse tables must come from the served world; refuse rather than answer about another one."""
        with self._lock:
            if self._checked:
                return
            sql = f"SELECT fingerprint FROM `{self._project}.{self._dataset}.{META_TABLE}` LIMIT 1"  # noqa: S608 (validated id)
            rows = list(self._bq().query(sql).result())
            loaded = rows[0]["fingerprint"] if rows else None
            if loaded != self._fingerprint:
                raise GraphUnavailable(
                    f"graph tables are from world {loaded!r}, not the served world {self._fingerprint!r}"
                )
            self._checked = True

    def run(self, query: str, params: Mapping[str, Any]) -> GraphResult:
        from google.cloud import bigquery

        named = _lookup(query, params)
        started = time.perf_counter()
        try:
            self._check_fresh()
            config = bigquery.QueryJobConfig(
                query_parameters=[_param(bigquery, p, params[p]) for p in named.params],
                reservation=self._reservation,
            )
            job = self._bq().query(compose(named, graph=self.graph), job_config=config)
            rows = [dict(r.items()) for r in job.result()]
        except GraphUnavailable:
            raise
        except (
            Exception
        ) as exc:  # the warehouse said no; say so, with the reason, and show nothing from it
            _LOG.warning("graph query %s failed: %s", query, exc)
            raise GraphUnavailable(f"{query}: {exc}") from exc
        return GraphResult(
            rows,
            f"graph.bigquery:{self._project}.{self._dataset}.{GRAPH_NAME}",
            round(time.perf_counter() - started, 3),
            getattr(job, "slot_millis", None),
        )


def _param(bigquery: Any, name: str, value: Any) -> Any:
    kind = "INT64" if isinstance(value, int) and not isinstance(value, bool) else "STRING"
    return bigquery.ScalarQueryParameter(name, kind, value)


__all__ = [
    "BigQueryGraphStore",
    "GraphQueryRefused",
    "GraphResult",
    "GraphStore",
    "GraphUnavailable",
    "LocalGraphStore",
]
