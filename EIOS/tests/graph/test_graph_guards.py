"""The cost and availability guards around the BigQuery graph store: every job is labelled and has a timeout, a repeat
question is answered from a cache, and an unreachable warehouse falls back to the local double with the answer's source
saying so (never silently)."""

from __future__ import annotations

from typing import Any

import pytest

from eios.dataplane.aml_geo_sessions import HUB_DEGREE, MIN_EXIT_SESSIONS, MIN_SHARED_FOREIGN
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.graph.store import (
    JOB_TIMEOUT_MS,
    BigQueryGraphStore,
    CachedGraphStore,
    FallbackGraphStore,
    GraphQueryRefused,
    GraphUnavailable,
    LocalGraphStore,
)
from eios.graph.tables import GraphTables, build_tables

EXITS = {
    "hub_degree": HUB_DEGREE,
    "min_shared": MIN_SHARED_FOREIGN,
    "min_sessions": MIN_EXIT_SESSIONS,
}


@pytest.fixture(scope="module")
def tables() -> GraphTables:
    return build_tables(build_aml_world(AmlWorldConfig()), {"MM": "high"}, {"NG": "Nigeria"})


class _Rows:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def result(self) -> list[dict[str, Any]]:
        return self._rows


class _Warehouse:
    """A fake BigQuery client: answers the freshness check, records each graph job, can be made to fail."""

    def __init__(self, fingerprint: str, fail: bool = False) -> None:
        self.fingerprint, self.fail, self.configs = fingerprint, fail, []

    def query(self, sql: str, job_config: Any = None) -> _Rows:
        if "_meta" in sql:
            return _Rows([{"fingerprint": self.fingerprint}])
        if self.fail:
            raise RuntimeError("the reservation is unavailable")
        self.configs.append(job_config)
        return _Rows([{"gateway_id": "GW-NG-X00"}])


def _bigquery(tables: GraphTables, warehouse: _Warehouse) -> BigQueryGraphStore:
    return BigQueryGraphStore(
        "test-project",
        "projects/p/locations/l/reservations/g",
        tables.fingerprint,
        client=warehouse,
    )


def test_every_graph_job_is_labelled_and_has_a_timeout(tables: GraphTables) -> None:
    warehouse = _Warehouse(tables.fingerprint)
    _bigquery(tables, warehouse).run("shared_exits", EXITS)
    config = warehouse.configs[0]
    assert config.labels == {"app": "eios", "component": "geo", "query": "shared_exits"}
    assert int(config.job_timeout_ms) == JOB_TIMEOUT_MS


def test_a_repeated_question_is_answered_from_the_cache_without_another_job(
    tables: GraphTables,
) -> None:
    warehouse = _Warehouse(tables.fingerprint)
    store = CachedGraphStore(_bigquery(tables, warehouse))
    first = store.run("shared_exits", EXITS)
    second = store.run("shared_exits", EXITS)
    assert len(warehouse.configs) == 1 and second.rows == first.rows
    store.run("shared_exits", {**EXITS, "min_shared": EXITS["min_shared"] + 1})
    assert len(warehouse.configs) == 2  # other parameters are another question


def test_a_caller_changing_a_returned_row_cannot_change_the_next_answer(
    tables: GraphTables,
) -> None:
    store = CachedGraphStore(_bigquery(tables, _Warehouse(tables.fingerprint)))
    store.run("shared_exits", EXITS).rows[0]["gateway_id"] = "tampered"
    assert store.run("shared_exits", EXITS).rows[0]["gateway_id"] == "GW-NG-X00"


def test_a_failed_job_is_not_cached(tables: GraphTables) -> None:
    warehouse = _Warehouse(tables.fingerprint, fail=True)
    store = CachedGraphStore(_bigquery(tables, warehouse))
    with pytest.raises(GraphUnavailable):
        store.run("shared_exits", EXITS)
    warehouse.fail = False
    assert store.run("shared_exits", EXITS).rows  # the next try reaches the warehouse


def test_an_unreachable_warehouse_falls_back_to_the_local_double_and_the_source_says_so(
    tables: GraphTables,
) -> None:
    store = FallbackGraphStore(
        _bigquery(tables, _Warehouse(tables.fingerprint, fail=True)), LocalGraphStore(tables)
    )
    result = store.run("shared_exits", EXITS)
    assert result.source.startswith("graph.local:") and result.rows


def test_a_refused_query_is_never_hidden_by_the_fallback(tables: GraphTables) -> None:
    store = FallbackGraphStore(
        _bigquery(tables, _Warehouse(tables.fingerprint)), LocalGraphStore(tables)
    )
    with pytest.raises(GraphQueryRefused):
        store.run("no_such_query", {})
