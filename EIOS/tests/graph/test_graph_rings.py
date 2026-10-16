"""The ring around a shared exit and the accounts one hop from a country: graph queries checked against the frames."""

from __future__ import annotations

import pandas as pd
import pytest

from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.graph.queries import CATALOGUE, compose
from eios.graph.store import LocalGraphStore
from eios.graph.tables import GraphTables, build_tables

TIERS = {"MM": "high", "VG": "medium", "IQ": "medium"}
RING_EXIT = "GW-NG-X00"  # the planted shared exit in Nigeria


@pytest.fixture(scope="module")
def tables() -> GraphTables:
    return build_tables(build_aml_world(AmlWorldConfig()), TIERS)


@pytest.fixture(scope="module")
def local(tables: GraphTables) -> LocalGraphStore:
    return LocalGraphStore(tables)


def _linked(tables: GraphTables, sources: set[str]) -> set[str]:
    """Accounts sharing a non-hub identifier with any of `sources`, derived with pandas from the frames."""
    uses, idents = tables.frames["uses"], tables.frames["identifier"]
    quiet = set(idents.loc[~idents["hub"], "identifier_id"])
    mine = uses[uses["account_id"].isin(sources) & uses["identifier_id"].isin(quiet)]
    return set(uses[uses["identifier_id"].isin(mine["identifier_id"])]["account_id"]) - sources


def test_an_exit_ring_is_its_users_then_the_accounts_sharing_an_identifier_with_them(
    tables: GraphTables, local: LocalGraphStore
) -> None:
    rows = local.run("exit_ring", {"gateway": RING_EXIT}).rows
    logins = tables.frames["logged_in_via"]
    users = set(logins.loc[logins["gateway_id"] == RING_EXIT, "account_id"])
    assert {r["account_id"] for r in rows if r["via"] == "exit"} == users
    linked = {r["account_id"] for r in rows if r["via"] == "identifier"}
    assert linked == _linked(tables, users)
    assert not linked & users
    assert all(r["sessions"] > 0 for r in rows if r["via"] == "exit")
    assert all(r["sessions"] == 0 for r in rows if r["via"] == "identifier")


def test_an_exit_ring_never_links_through_a_hub(
    tables: GraphTables, local: LocalGraphStore
) -> None:
    hubs = set(tables.frames["identifier"].query("hub")["identifier_id"])
    rows = local.run("exit_ring", {"gateway": RING_EXIT}).rows
    assert not {r["link"] for r in rows if r["via"] == "identifier"} & hubs
    # a hub gateway is no exit at all: the privacy VPN shared by more than the RL-4 line of accounts
    assert local.run("exit_ring", {"gateway": "GW-NL-V01"}).rows == []


def test_country_links_are_one_hop_from_the_accounts_the_country_touches(
    tables: GraphTables, local: LocalGraphStore
) -> None:
    f = tables.frames
    gateways = set(f["located_in"].loc[f["located_in"]["iso2"] == "NG", "gateway_id"])
    direct = (
        set(f["registered_in"].loc[f["registered_in"]["iso2"] == "NG", "account_id"])
        | set(f["paid_via"].loc[f["paid_via"]["iso2"] == "NG", "account_id"])
        | set(f["logged_in_via"].loc[f["logged_in_via"]["gateway_id"].isin(gateways), "account_id"])
    )
    rows = local.run("country_links", {"countries": ["NG"]}).rows
    assert {r["account_id"] for r in rows} == _linked(tables, direct)
    assert all(r["source_account"] in direct and r["country"] == "NG" for r in rows)
    assert len({r["account_id"] for r in rows}) == len(rows)  # one row per linked account


def test_several_countries_are_answered_in_one_query_each_on_its_own(
    local: LocalGraphStore,
) -> None:
    both = local.run("country_links", {"countries": ["NG", "ZA"]}).rows
    alone = {
        c: {r["account_id"] for r in local.run("country_links", {"countries": [c]}).rows}
        for c in ("NG", "ZA")
    }
    for country, accounts in alone.items():
        assert {r["account_id"] for r in both if r["country"] == country} == accounts


def test_a_country_nothing_touches_has_no_links(local: LocalGraphStore) -> None:
    assert local.run("country_links", {"countries": ["AQ"]}).rows == []
    assert local.run("country_links", {"countries": []}).rows == []


@pytest.mark.parametrize("name", ["exit_ring", "country_links"])
def test_on_bigquery_the_traversals_are_gql_anchored_at_the_named_node(name: str) -> None:
    sql = compose(CATALOGUE[name], graph="`p.warm_graph.aml_geo`")
    assert sql.count("GRAPH_TABLE(") == len(CATALOGUE[name].traversals)
    for table in ("uses", "logged_in_via", "registered_in", "paid_via", "located_in"):
        assert f"FROM {table}" not in sql and f"JOIN {table}" not in sql  # traversals, not joins
    anchor = "@gateway" if name == "exit_ring" else "IN UNNEST(@countries)"
    assert all(anchor in t.gql for t in CATALOGUE[name].traversals.values())


def test_a_list_parameter_is_bound_as_a_string_array_on_bigquery() -> None:
    from google.cloud import bigquery

    from eios.graph.store import _param

    bound = _param(bigquery, "countries", ["NG", "ZA"])
    assert isinstance(bound, bigquery.ArrayQueryParameter)
    assert bound.array_type == "STRING" and bound.values == ["NG", "ZA"]
    assert isinstance(_param(bigquery, "gateway", "GW-NG-X00"), bigquery.ScalarQueryParameter)


def test_the_local_double_returns_plain_python_values(local: LocalGraphStore) -> None:
    rows = local.run("exit_ring", {"gateway": RING_EXIT}).rows
    assert rows and all(isinstance(r["sessions"], int) for r in rows)
    assert not any(isinstance(v, type(pd.NA)) for r in rows for v in r.values())
