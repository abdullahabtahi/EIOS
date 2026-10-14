"""What surrounds a case on the AML screen is read from the engine for that account, never sampled (spec 031 FR-011)."""

import pytest

from eios.cockpit import aml_case_extras as extras
from eios.cockpit import aml_engine_view as view
from eios.dataplane.aml_engine import run_aml_engine
from eios.dataplane.aml_insights import node_insights
from eios.dataplane.aml_service import EngineAMLService
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.ontology.omcp.port.proposals import hold_stage_request


@pytest.fixture(scope="module")
def engine() -> EngineAMLService:
    return EngineAMLService(run_aml_engine(build_aml_world(AmlWorldConfig())))


def test_the_evidence_strip_states_the_story_account_numbers(engine: EngineAMLService) -> None:
    strip = extras.evidence_strip(engine, "CR84920")
    tiles = {t["label"]: t for t in strip["tiles"]}
    assert strip["title"].endswith("(SG)") and strip["severity"] == "CRITICAL"
    assert tiles["30-day deposits"]["value"] == "$8,000" and tiles["30-day deposits"][
        "caption"
    ].startswith("16.0x")
    assert tiles["Network"]["value"] == "23 accounts" and tiles["Network"]["tone"] == "alert"
    assert {m["metric_id"] for m in strip["metrics"]} == {
        "realized_deposit_volume_30d_usd",
        "discrepancy_multiplier",
    }


def test_the_strip_differs_between_accounts_and_shows_no_score_without_an_alert(
    engine: EngineAMLService,
) -> None:
    a, b = (extras.evidence_strip(engine, r["entity_id"]) for r in engine.get_triage_cases(0, 2))
    assert a["title"] != b["title"] and a["tiles"] != b["tiles"]
    quiet = next(c for c in engine.account_ids() if engine.snapshot.case_for(c) is None)
    strip = extras.evidence_strip(engine, quiet)
    assert strip["score"] is None and strip["severity"] == "NONE"


def test_the_sar_panel_carries_the_engine_narrative_and_says_why_it_has_no_citations(
    engine: EngineAMLService,
) -> None:
    panel = extras.sar_panel(engine, "CR84920")
    assert "$8,000.00" in panel["summaryNarrative"] and panel["subjectAccountId"] == "CR84920"
    assert panel["statutoryCitations"] == [] and panel["statutoryNote"] == extras.STATUTORY_NOTE
    assert "netLossProfitRatio" not in panel  # no such ratio is computed, so none is shown
    assert panel["transactionHistorySummary"].startswith(
        "16 deposits and 1 withdrawal in 30 days; 0 trades"
    )


def test_a_trade_off_exists_only_when_a_withdrawal_is_pending_and_carries_a_real_request(
    engine: EngineAMLService,
) -> None:
    [offer] = extras.trade_offs(engine, "CR84920")
    assert offer["stageRequest"]["metadata"]["txn_id"] == "W-84920-1"
    assert "$7,800" in offer["projectedReturn"] and 0 < offer["confidenceScore"] <= 1
    clean = next(a for a in engine.account_ids() if engine.get_pending_withdrawal(a) is None)
    assert extras.trade_offs(engine, clean) == []


def test_stage_requests_match_what_the_assistant_would_stage(engine: EngineAMLService) -> None:
    actions = extras.case_actions(engine, "CR84920")
    assert (
        actions["hold"]["action_type"] == "HoldWithdrawal"
        and actions["hold"]["requires_four_eyes"] is True
    )
    assert (
        actions["hold"]["metadata"]["txn_id"]
        == hold_stage_request("CR84920", "W-84920-1")["metadata"]["txn_id"]
    )
    assert actions["file_sar"]["action_type"] == "FileSARDraft"
    clean = next(a for a in engine.account_ids() if engine.get_pending_withdrawal(a) is None)
    assert extras.case_actions(engine, clean)["hold"] is None


def test_node_insights_are_computed_from_the_network_and_claim_no_risk_for_a_gateway(
    engine: EngineAMLService,
) -> None:
    graph = engine.get_kinetic_network_graph("CR84920")
    insights = node_insights(engine.snapshot, graph)
    assert set(insights) == {n.node_id for n in graph.nodes}
    seed = insights["CR84920"]
    assert seed["country"] == "SG" and seed["velocity_usd"] == 8000.0 and 0.9 < seed["risk"] <= 1.0
    assert 0.0 <= seed["betweenness"] <= 1.0
    hub = insights["PA-HUB-007"]
    assert hub["risk"] is None and hub["country"] is None and hub["velocity_usd"] is None


def test_the_case_payload_has_everything_the_screen_reads(engine: EngineAMLService) -> None:
    payload = view.case_payload(engine, "CR91204")
    assert {
        "active_dossier",
        "kinetic_canvas",
        "evidence_strip",
        "sar_draft",
        "case_actions",
    } <= set(payload)
    dossier = payload["active_dossier"]
    assert dossier["sar_draft"]["subjectAccountId"] == "CR91204" and dossier["trade_offs"]
    assert payload["case_actions"]["hold"]["metadata"]["txn_id"] == "W-91204-1"
    assert all(
        m["origin_engine"] != "AMLHotState.DuckDB"
        for s in dossier["sections"]
        for m in s["metrics"]
    )
