"""Geography as case evidence: overview, leads, exits with their ring, corridors, jurisdictions and list changes."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from eios.dataplane.aml_geo import GeoSnapshot, run_geo_engine
from eios.dataplane.geo_evidence import (
    corridor,
    gateways_of,
    jurisdiction,
    leads,
    overview,
    shared_exit,
)
from eios.dataplane.geo_lists import list_change, shares
from eios.dataplane.geo_readmodel import curated_tiers
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.graph.store import GraphResult, GraphUnavailable, LocalGraphStore
from eios.graph.tables import build_tables
from eios.reference.editions import ListId, curated_reference, editions

CENTROIDS = Path(__file__).parents[1] / "fixtures" / "geo" / "country_centroids.json"
POSITIONS = {c: (p[0], p[1]) for c, p in json.loads(CENTROIDS.read_text())["positions"].items()}
TRUTH_WORDS = ("malicious", "mule", "ring_member", "traveller", "planted", "truth")
REF = curated_reference()


@pytest.fixture(scope="module")
def snap() -> GeoSnapshot:
    return run_geo_engine(build_aml_world(AmlWorldConfig()), curated_tiers(), POSITIONS)


@pytest.fixture(scope="module")
def store(snap: GeoSnapshot) -> LocalGraphStore:
    return LocalGraphStore(build_tables(snap.world, snap.tiers))


class _Down:
    backend = "bigquery"

    def run(self, query: str, params: Mapping[str, Any]) -> GraphResult:
        raise GraphUnavailable("warehouse unreachable")


def _no_truth(payload: Any) -> None:
    text = json.dumps(payload).lower()
    assert not [w for w in TRUTH_WORDS if w in text]


def test_the_overview_counts_every_lens_and_how_many_it_can_judge(snap: GeoSnapshot) -> None:
    o = overview(snap)
    _no_truth(o)
    lenses = {lens["lens"]: lens for lens in o["lenses"]}
    c = snap.clients
    assert lenses["shared_exit"]["flagged"] == int(c["exit_flag"].sum())
    assert lenses["login_country"]["assessable"] == int(c["mismatch_assessable"].sum()) < len(c)
    assert lenses["impossible_travel"]["flagged"] == int(c["jump_flag"].sum())
    assert o["shared_exits"] == len(gateways_of(snap)) == 6
    assert [e["accounts"] for e in o["top_exits"]] == sorted(
        (e["accounts"] for e in o["top_exits"]), reverse=True
    )
    assert all(r["tier"] in {"high", "medium"} for r in o["top_corridors"])


def test_without_positions_travel_is_not_assessable_not_zero() -> None:
    blind = run_geo_engine(build_aml_world(AmlWorldConfig()), curated_tiers())
    travel = next(x for x in overview(blind)["lenses"] if x["lens"] == "impossible_travel")
    assert travel == {"lens": "impossible_travel", "flagged": None, "assessable": None}


def test_corridor_leads_follow_the_maps_order(snap: GeoSnapshot) -> None:
    rows = leads(snap, "corridor", 60)
    rank = [{"high": 2, "medium": 1}.get(r["tier"] or "", 0) for r in rows]
    assert rank == sorted(rank, reverse=True)
    elevated = [r for r in rows if r["tier"] == "high"]
    assert [r["volume_usd"] for r in elevated] == sorted(
        (r["volume_usd"] for r in elevated), reverse=True
    )
    assert all(r["corridor_id"] == f"{r['origin']}>{r['destination']}" for r in rows)


def test_login_and_account_leads_name_what_the_map_can_select(snap: GeoSnapshot) -> None:
    pairs = leads(snap, "login_country", 5)
    assert pairs[0]["pair_id"] == f"{pairs[0]['kyc_country']}>{pairs[0]['ip_country']}"
    accounts = leads(snap, "account", 5)
    assert len(accounts) == 5 and all(a["flags"] and a["geo_score"] > 0 for a in accounts)
    with pytest.raises(ValueError):
        leads(snap, "everything", 5)


def test_a_shared_exit_shows_its_users_the_rule_and_the_ring_from_the_graph(
    snap: GeoSnapshot, store: LocalGraphStore
) -> None:
    e = shared_exit(snap, store, REF, "GW-NG-X00")
    assert e is not None
    _no_truth(e)
    listed = next(g for g in gateways_of(snap) if g["gateway_id"] == "GW-NG-X00")
    assert e["flagged_accounts"] == listed["accounts"] and not e["hub"] and e["shared_exit"]
    assert e["country"]["name"] == "Nigeria"
    assert sum(h["accounts"] for h in e["home_countries"]) == e["flagged_accounts"]
    assert e["rule"]["min_shared_accounts"] >= 2 and e["rule"]["hub_degree"] > 0
    ring = e["ring"]
    assert ring["error"] is None and ring["source"] == "graph.local:aml_geo"
    assert ring["graph_users"] >= e["flagged_accounts"]
    assert ring["linked_total"] >= len(ring["linked"])


def test_a_hub_is_named_a_hub_and_ties_nobody_together(
    snap: GeoSnapshot, store: LocalGraphStore
) -> None:
    hub = shared_exit(snap, store, REF, "GW-NL-V01")
    assert hub is not None and hub["hub"] and not hub["shared_exit"] and hub["ring"] is None
    assert shared_exit(snap, store, REF, "GW-XX-X99") is None


def test_a_graph_outage_empties_only_the_ring(snap: GeoSnapshot) -> None:
    e = shared_exit(snap, _Down(), REF, "GW-NG-X00")
    assert e is not None and e["flagged_accounts"] > 0
    assert e["ring"]["linked"] is None and "unreachable" in e["ring"]["error"]


def test_a_corridor_gives_both_ends_standing_and_its_largest_accounts(snap: GeoSnapshot) -> None:
    c = corridor(snap, REF, "ID", "MM")
    assert c is not None
    assert c["tier"] == "high" and c["destination"]["fatf_list"] == "call_for_action"
    assert c["deposits"] + c["withdrawals"] == c["events"]
    assert sum(a["volume_usd"] for a in c["top_accounts"]) <= c["volume_usd"] + 0.01
    assert corridor(snap, REF, "AQ", "MM") is None  # no money moves on it: no such corridor


def test_a_jurisdiction_reports_measured_exposure_and_list_standing(snap: GeoSnapshot) -> None:
    ng = jurisdiction(snap, REF, "NG")
    assert ng["registered_accounts"] == int((snap.world.clients["country"] == "NG").sum()) > 0
    assert "GW-NG-X00" in ng["shared_exits"]
    assert ng["standing"]["eu_high_risk"] is False  # removed by Delegated Regulation 2026/83
    nothing = jurisdiction(snap, REF, "AQ")
    assert nothing["exposed_accounts"] == 0 and nothing["sessions"] == 0  # measured zero
    assert nothing["standing"]["basel_score"] is None  # unrated, never low


def test_the_june_fatf_plenary_reaches_the_ring_exit_in_iraq(
    snap: GeoSnapshot, store: LocalGraphStore
) -> None:
    out = list_change(snap, store, editions(ListId.FATF))
    _no_truth(out)
    added = {r["iso2"]: r for r in out["added"]["countries"]}
    assert set(added) == {"IQ", "BA"}
    assert "GW-IQ-X02" in added["IQ"]["shared_exits"]
    assert added["IQ"]["login_accounts"] > 0 and added["IQ"]["linked_accounts"] is not None
    assert sum(out["added"]["session_shares"].values()) == pytest.approx(100.0)
    removed = {r["iso2"]: r for r in out["removed"]["countries"]}
    assert removed["NA"]["exposed_accounts"] == 0 and removed["NA"]["linked_accounts"] == 0
    assert out["graph"]["source"] == "graph.local:aml_geo"


def test_the_eu_amendment_delisted_nigeria_while_its_exit_is_still_used(
    snap: GeoSnapshot, store: LocalGraphStore
) -> None:
    out = list_change(snap, store, editions(ListId.EU))
    removed = {r["iso2"]: r for r in out["removed"]["countries"]}
    assert removed["NG"]["registered_accounts"] > 0 and "GW-NG-X00" in removed["NG"]["shared_exits"]
    added = {r["iso2"]: r for r in out["added"]["countries"]}
    assert added["VG"]["payment_volume_usd"] > 0  # the wash-trading hop is newly listed
    assert out["added"]["payment_shares"] == {"BO": 0.0, "RU": 0.0, "VG": 100.0}


def test_a_list_change_survives_a_graph_outage_with_the_links_unknown(snap: GeoSnapshot) -> None:
    out = list_change(snap, _Down(), editions(ListId.EU))
    ng = next(r for r in out["removed"]["countries"] if r["iso2"] == "NG")
    assert ng["linked_accounts"] is None and ng["registered_accounts"] > 0
    assert "unreachable" in out["graph"]["error"]


@pytest.mark.parametrize(
    "values",
    [{"a": 1, "b": 1, "c": 1}, {"a": 133, "b": 36}, {"a": 0.5, "b": 0.25, "c": 0.25}, {"x": 7}],
)
def test_shares_sum_to_exactly_one_hundred(values: dict[str, float]) -> None:
    found = shares(values)
    assert found is not None and round(sum(v * 10 for v in found.values())) == 1000


def test_nothing_to_attribute_is_none_not_an_equal_split() -> None:
    assert shares({"a": 0, "b": 0}) is None and shares({}) is None
