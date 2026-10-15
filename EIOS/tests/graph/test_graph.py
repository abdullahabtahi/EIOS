"""The AML world as a property graph: tables from the frames, named queries, and two runners that must agree."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from eios.dataplane.aml_geo import run_geo_engine
from eios.dataplane.aml_geo_sessions import HUB_DEGREE, MIN_EXIT_SESSIONS, MIN_SHARED_FOREIGN
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import AmlWorld, build_aml_world
from eios.graph.queries import CATALOGUE, compose
from eios.graph.store import (
    BigQueryGraphStore,
    GraphQueryRefused,
    GraphUnavailable,
    LocalGraphStore,
)
from eios.graph.tables import (
    EDGE_TABLES,
    NODE_TABLES,
    GraphTables,
    build_tables,
    property_graph_ddl,
)

EXITS = {
    "hub_degree": HUB_DEGREE,
    "min_shared": MIN_SHARED_FOREIGN,
    "min_sessions": MIN_EXIT_SESSIONS,
}
TIERS = {"MM": "high", "VG": "medium", "IQ": "medium"}


@pytest.fixture(scope="module")
def world() -> AmlWorld:
    return build_aml_world(AmlWorldConfig())


@pytest.fixture(scope="module")
def tables(world: AmlWorld) -> GraphTables:
    return build_tables(world, TIERS, {"NG": "Nigeria"})


@pytest.fixture(scope="module")
def local(tables: GraphTables) -> LocalGraphStore:
    return LocalGraphStore(tables)


def test_tables_cover_every_node_and_edge_and_hold_no_truth(
    world: AmlWorld, tables: GraphTables
) -> None:
    assert set(tables.frames) == set(NODE_TABLES) | set(EDGE_TABLES)
    assert len(tables.frames["account"]) == len(world.clients)
    assert tables.fingerprint == world.config.fingerprint()
    columns = {c.lower() for f in tables.frames.values() for c in f.columns}
    assert not {"malicious", "ring", "truth", "traveller", "mule"} & columns


def test_every_edge_points_at_a_node_that_exists(tables: GraphTables) -> None:
    f = tables.frames
    accounts, gateways = set(f["account"]["account_id"]), set(f["gateway"]["gateway_id"])
    countries, idents = set(f["country"]["iso2"]), set(f["identifier"]["identifier_id"])
    assert (
        set(f["logged_in_via"]["account_id"]) <= accounts
        and set(f["logged_in_via"]["gateway_id"]) <= gateways
    )
    assert set(f["located_in"]["iso2"]) <= countries and set(f["paid_via"]["iso2"]) <= countries
    assert set(f["uses"]["account_id"]) <= accounts and set(f["uses"]["identifier_id"]) <= idents


def test_unrated_countries_are_null_never_low(tables: GraphTables) -> None:
    tiers = tables.frames["country"].set_index("iso2")["tier"]
    assert tiers["MM"] == "high" and tiers["IQ"] == "medium"
    assert pd.isna(tiers["SG"])  # missing, loaded as NULL


def test_hubs_follow_the_rl4_line(tables: GraphTables) -> None:
    g = tables.frames["gateway"]
    assert (g["hub"] == (g["accounts"] > HUB_DEGREE)).all()
    assert g.set_index("gateway_id").loc["GW-NL-V01", "hub"]  # the privacy VPN exit
    i = tables.frames["identifier"]
    assert i["hub"].any()  # carrier-grade NAT addresses


def test_the_ddl_declares_every_table_with_its_label(tables: GraphTables) -> None:
    ddl = property_graph_ddl("test-project")
    assert ddl.startswith("CREATE OR REPLACE PROPERTY GRAPH `test-project.warm_graph.aml_geo`")
    for label in (
        "Account",
        "Country",
        "Gateway",
        "Identifier",
        "LOGGED_IN_VIA",
        "LOCATED_IN",
        "PAID_VIA",
        "USES",
        "REGISTERED_IN",
    ):
        assert f"LABEL {label}" in ddl


def test_the_graph_finds_the_same_shared_exit_accounts_as_the_engine(
    world: AmlWorld, local: LocalGraphStore
) -> None:
    """Two independent derivations, one from the frames as a graph, one from the engine's session lens."""
    graph = {r["account_id"] for r in local.run("shared_exits", EXITS).rows}
    snap = run_geo_engine(world, TIERS)
    engine = set(snap.clients.loc[snap.clients["exit_flag"], "client_id"])
    assert graph == engine and len(graph) > 50


def test_an_accounts_neighbourhood_skips_hubs(local: LocalGraphStore, tables: GraphTables) -> None:
    rows = local.run("account_neighbourhood", {"account": "CR84920"}).rows
    assert rows and all(r["account_id"] != "CR84920" for r in rows)
    hubs = set(tables.frames["gateway"].query("hub")["gateway_id"]) | set(
        tables.frames["identifier"].query("hub")["identifier_id"]
    )
    assert not {r["link"] for r in rows} & hubs
    assert {"gateway", "identifier"} >= {r["via"] for r in rows}


def test_unknown_queries_and_missing_parameters_are_refused(local: LocalGraphStore) -> None:
    with pytest.raises(GraphQueryRefused):
        local.run("drop_everything", {})
    with pytest.raises(GraphQueryRefused):
        local.run("account_neighbourhood", {})


def test_bigquery_traversals_are_gql_through_graph_table() -> None:
    sql = compose(CATALOGUE["shared_exits"], graph="`p.warm_graph.aml_geo`")
    assert "GRAPH_TABLE(" in sql and "MATCH (a:Account)-[v:LOGGED_IN_VIA]->(g:Gateway)" in sql
    assert "@hub_degree" in sql and "logged_in_via v JOIN" not in sql


class _Rows:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def result(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeBigQuery:
    def __init__(self, fingerprint: str) -> None:
        self.fingerprint = fingerprint
        self.configs: list[Any] = []

    def query(self, sql: str, job_config: Any = None) -> _Rows:
        if "_meta" in sql:
            return _Rows([{"fingerprint": self.fingerprint}])
        self.configs.append(job_config)
        return _Rows([])


def test_bigquery_jobs_run_on_the_named_reservation(tables: GraphTables) -> None:
    fake = _FakeBigQuery(tables.fingerprint)
    store = BigQueryGraphStore(
        "test-project",
        "projects/test-project/locations/us-central1/reservations/g",
        tables.fingerprint,
        client=fake,
    )
    result = store.run("account_neighbourhood", {"account": "CR84920"})
    assert fake.configs[0].reservation.endswith("/reservations/g")
    assert result.source == "graph.bigquery:test-project.warm_graph.aml_geo"


def test_tables_from_another_world_are_refused_not_used(tables: GraphTables) -> None:
    store = BigQueryGraphStore(
        "test-project", "r", tables.fingerprint, client=_FakeBigQuery("another-world")
    )
    with pytest.raises(GraphUnavailable, match="another-world"):
        store.run("shared_exits", EXITS)


@pytest.mark.requires_cloud
def test_live_bigquery_graph_agrees_with_the_local_double(monkeypatch: pytest.MonkeyPatch) -> None:
    """Against the warehouse loaded by `python -m eios.graph load`: the served world, GQL on the reservation."""
    project, reservation = (
        os.environ.get("EIOS_GRAPH_PROJECT"),
        os.environ.get("EIOS_GRAPH_RESERVATION"),
    )
    if not (project and reservation):
        pytest.skip("EIOS_GRAPH_PROJECT and EIOS_GRAPH_RESERVATION are needed")
    from eios.dataplane import geo_plane

    monkeypatch.setenv("EIOS_DATA_PLANE", "engine")
    geo_plane.reset_for_testing()
    served = geo_plane.graph_tables()
    assert served is not None
    remote, here = (
        BigQueryGraphStore(project, reservation, served.fingerprint),
        LocalGraphStore(served),
    )
    key = lambda rows: sorted(tuple(r.values()) for r in rows)  # noqa: E731
    assert key(remote.run("shared_exits", EXITS).rows) == key(here.run("shared_exits", EXITS).rows)
    n = {"account": "CR84920"}
    assert key(remote.run("account_neighbourhood", n).rows) == key(
        here.run("account_neighbourhood", n).rows
    )
    geo_plane.reset_for_testing()


def test_country_centroid_fixture_is_grounded() -> None:
    data = json.loads(
        (Path(__file__).parents[1] / "fixtures" / "geo" / "country_centroids.json").read_text()
    )
    assert "Overture" in data["source"] and len(data["positions"]) >= 40
