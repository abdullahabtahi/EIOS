"""The geo capabilities through the governed port: scope, arguments, envelopes, map targets and honest failures."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from eios.dataplane.geo_evidence import LEAD_KINDS
from eios.ontology.omcp.port.catalogue import all_specs, build_port
from eios.ontology.omcp.port.contracts import ToolErrorCode
from eios.ontology.omcp.port.geo_account import _benign
from eios.ontology.omcp.port.geo_tools import LeadKind
from eios.ontology.omcp.port.principal import Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.service import GovernedToolPort
from tests.ontology.port.conftest import seeded_geo, who

GEO = who("geospatial")
GEO_TOOLS = {s.name for s in all_specs() if s.capability.startswith("geo.")}


def _call(port: GovernedToolPort, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    outcome = port.call(GEO, tool, args)
    assert outcome.error is None, outcome.error
    return outcome.payload()


def _targets(payload: dict[str, Any]) -> set[tuple[str, str]]:
    return {(t["kind"], t["target_id"]) for t in payload["map_targets"]}


def test_the_geo_tools_are_the_geospatial_workstations_alone(port: GovernedToolPort) -> None:
    offered = {s.name for s in port.list_tools(GEO)}
    assert GEO_TOOLS <= offered and len(GEO_TOOLS) == 7
    assert {"get_aml_dossier", "propose_hold", "draft_sar", "search_regulations"} <= offered
    for workstation in Workstation:
        if workstation is not Workstation.GEOSPATIAL:
            assert not GEO_TOOLS & {s.name for s in port.list_tools(who(workstation.value))}
    aml = {s.name for s in port.list_tools(who("aml_investigator"))}
    assert len(aml) <= 13  # the AML assistant's toolset did not grow


def test_lead_kinds_are_one_vocabulary_with_the_evidence_module() -> None:
    assert {k.value for k in LeadKind} == set(LEAD_KINDS)


def test_a_shared_exit_comes_with_its_envelope_its_facts_and_its_map_targets(
    port: GovernedToolPort,
) -> None:
    p = _call(port, "get_shared_exit", {"gateway_id": "gw-ng-x00"})  # the map's id, any case
    assert p["capability"] == "geo.exit" and p["entity_id"] == "GW-NG-X00"
    assert p["as_of"].startswith("2026-10-14")  # the world's as-of, not the wall clock
    assert p["fact_ids"]["flagged_accounts"] == "geo.exit:GW-NG-X00:flagged_accounts"
    assert ("gateway", "GW-NG-X00") in _targets(p) and ("country", "NG") in _targets(p)
    assert p["ring"]["source"] == "graph.local:aml_geo" and p["ring"]["linked_total"] >= 0
    assert p["home_country_count"] == len(p["home_countries"])


@pytest.mark.parametrize(
    ("tool", "args", "field"),
    [
        ("get_shared_exit", {"gateway_id": "Nigeria exit"}, "gateway_id"),
        ("get_corridor", {"corridor_id": "Indonesia to Myanmar"}, "corridor_id"),
        ("get_jurisdiction", {"country_id": "Nigeria"}, "country_id"),
        ("get_geo_account", {"entity_id": "11568"}, "entity_id"),
        ("list_geo_leads", {"kind": "everything"}, "kind"),
        ("get_list_change_impact", {"list_id": "ofac"}, "list_id"),
    ],
)
def test_a_wrong_shape_is_refused_naming_the_field(
    port: GovernedToolPort, tool: str, args: dict[str, Any], field: str
) -> None:
    outcome = port.call(GEO, tool, args)
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.INVALID_ARGUMENTS
    assert field in outcome.error.message


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("get_shared_exit", {"gateway_id": "GW-XX-X99"}),
        ("get_corridor", {"corridor_id": "AQ>MM"}),
        ("get_geo_account", {"entity_id": "CR00000000"}),
    ],
)
def test_something_this_book_does_not_hold_is_not_found(
    port: GovernedToolPort, tool: str, args: dict[str, Any]
) -> None:
    outcome = port.call(GEO, tool, args)
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.NOT_FOUND


def test_without_a_geo_plane_every_geo_tool_says_so() -> None:
    bare = build_port(ReadModels.default())
    outcome = bare.call(GEO, "get_geo_overview", {})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.DATA_UNAVAILABLE


def test_the_overview_offers_the_map_its_top_leads(port: GovernedToolPort) -> None:
    p = _call(port, "get_geo_overview", {})
    kinds = {k for k, _ in _targets(p)}
    assert {"gateway", "corridor", "account"} <= kinds
    assert p["units"]["lenses[].flagged"] == "accounts"


def test_a_corridor_names_both_ends_on_every_list(port: GovernedToolPort) -> None:
    p = _call(port, "get_corridor", {"corridor_id": "ID>MM"})
    assert p["tier"] == "high" and p["destination"]["fatf_list"] == "call_for_action"
    assert ("corridor", "ID>MM") in _targets(p)


def test_an_account_carries_each_lens_finding_and_the_rule_behind_it(
    port: GovernedToolPort,
) -> None:
    p = _call(port, "get_geo_account", {"entity_id": "CR11568"})
    findings = {f["lens"]: f for f in p["findings"]}
    assert findings["shared_exit"]["flag"] and findings["impossible_travel"]["flag"]
    assert p["rule"]["min_jumps"] >= 2 and p["rule"]["max_speed_kmh"] > 0
    assert p["jumps"]["examples"][0]["km"] >= p["rule"]["min_jump_km"]
    assert ("gateway", p["exit_gateway_id"]) in _targets(p)
    assert p["neighbourhood"]["source"] == "graph.local:aml_geo"


def test_a_ring_member_is_not_offered_the_travel_excuse_and_readings_carry_no_number(
    port: GovernedToolPort,
) -> None:
    p = _call(port, "get_geo_account", {"entity_id": "CR11568"})
    codes = {r["code"] for r in p["benign_readings"]}
    assert "single_country_abroad" not in codes  # its logins abroad go through a shared exit
    assert not any(
        ch.isdigit() for r in p["benign_readings"] for ch in r["reading"].replace("RL-4", "")
    )


def _evidence(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "kyc_country": "TH",
        "gateways": [{"gateway_id": "GW-TH-R01", "hub": False}],
        "jumps": {"count": 1, "via_hub": 0, "examples": []},
        "login_countries": [{"iso2": "TH", "sessions": 9}, {"iso2": "JP", "sessions": 3}],
        "payments": [],
    }
    return {**base, **overrides}


@pytest.mark.parametrize(
    ("evidence", "exit_flagged", "codes"),
    [
        (_evidence(), False, ["single_country_abroad", "no_money_abroad"]),  # a trip, nothing else
        (_evidence(), True, ["no_money_abroad"]),  # abroad through a shared exit: not a trip
        (
            _evidence(
                gateways=[{"gateway_id": "GW-TH-C01", "hub": True}],
                jumps={"count": 2, "via_hub": 2, "examples": []},
                payments=[{"iso2": "MM"}],
            ),
            False,
            ["shared_infrastructure", "hub_position", "single_country_abroad"],
        ),
    ],
)
def test_benign_readings_are_read_from_the_evidence(
    evidence: dict[str, Any], exit_flagged: bool, codes: list[str]
) -> None:
    assert [r["code"] for r in _benign(evidence, exit_flagged)] == codes


def test_a_jurisdiction_says_which_reference_layer_it_read(port: GovernedToolPort) -> None:
    p = _call(port, "get_jurisdiction", {"country_id": "iq"})
    assert p["entity_id"] == "IQ" and p["standing"]["fatf_list"] == "increased_monitoring"
    assert "curated" in p["reference_layer"]
    assert ("gateway", "GW-IQ-X02") in _targets(p)


def test_a_list_change_attributes_each_group_to_its_countries(port: GovernedToolPort) -> None:
    p = _call(port, "get_list_change_impact", {"list_id": "eu"})
    added = {r["iso2"]: r for r in p["added"]["countries"]}
    assert added["VG"]["payment_share_pct"] == 100.0
    removed = {r["iso2"]: r for r in p["removed"]["countries"]}
    assert removed["NG"]["linked_accounts"] is not None
    shares = [
        r["session_share_pct"]
        for r in p["removed"]["countries"]
        if r["session_share_pct"] is not None
    ]
    assert sum(shares) == pytest.approx(100.0)
    assert ("country", "NG") in _targets(p) and ("gateway", "GW-NG-X00") in _targets(p)


def test_leads_of_each_kind_name_what_the_map_selects(port: GovernedToolPort) -> None:
    expect = {
        "shared_exit": "gateway",
        "corridor": "corridor",
        "login_country": "mismatch",
        "account": "account",
    }
    for kind, target_kind in expect.items():
        p = _call(port, "list_geo_leads", {"kind": kind, "limit": 3})
        assert p["shown"] == len(p["map_targets"]) <= 3
        assert {k for k, _ in _targets(p)} == {target_kind}


def test_the_served_origin_is_carried_on_every_result() -> None:
    engine = replace(seeded_geo(), origin=seeded_geo().origin.__class__("engine"))
    port = build_port(replace(ReadModels.default(), geo=engine))
    assert _call(port, "get_geo_overview", {})["data_origin"] == "engine"
