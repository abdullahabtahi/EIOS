"""On the engine plane the assistant's tools and the screen read the same objects and agree for any account (spec 031 SC-003)."""

from typing import Any

import pytest

from eios.cockpit import aml_engine_view as view
from eios.dataplane.aml_engine import run_aml_engine
from eios.dataplane.aml_service import EngineAMLService
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import DataOrigin, ToolErrorCode
from eios.ontology.omcp.port.principal import Principal, principal_for
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.service import GovernedToolPort

AML: Principal = principal_for("uid-test", "aml_investigator")


@pytest.fixture(scope="module")
def engine() -> EngineAMLService:
    return EngineAMLService(run_aml_engine(build_aml_world(AmlWorldConfig())))


@pytest.fixture(scope="module")
def port(engine: EngineAMLService) -> GovernedToolPort:
    models = ReadModels.over(engine, clock=lambda: engine.as_of, aml_origin=DataOrigin.ENGINE)
    return build_port(models)


def _ok(port: GovernedToolPort, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    outcome = port.call(AML, tool, args)
    assert outcome.error is None, outcome.error
    return outcome.payload()


def _metric(dossier: dict[str, Any], metric_id: str) -> float:
    for section in dossier["sections"]:
        for metric in section["metrics"]:
            if metric["metric_id"] == metric_id:
                return float(metric["raw_value"])
    raise AssertionError(metric_id)


def test_tools_and_screen_agree_for_twelve_different_alerts(
    engine: EngineAMLService, port: GovernedToolPort
) -> None:
    rows = engine.get_triage_cases(min_score=0, limit=12)
    assert len({r["entity_id"] for r in rows}) == 12
    for row in rows:
        entity = row["entity_id"]
        screen = view.active_dossier(engine, entity)
        tool = _ok(port, "get_aml_dossier", {"entity_id": entity})
        assert tool["data_origin"] == "engine"
        assert tool["realized_deposit_volume_30d_usd"] == _metric(
            screen, "realized_deposit_volume_30d_usd"
        )
        assert tool["discrepancy_multiplier"] == _metric(screen, "discrepancy_multiplier")
        assert tool["composite_risk_score"] == row["risk_score"]


def test_the_alert_list_is_the_ranked_queue_with_engine_origin(
    port: GovernedToolPort, engine: EngineAMLService
) -> None:
    got = _ok(port, "list_alerts", {"min_score": 0, "limit": 10})
    assert [a["entity_id"] for a in got["alerts"]] == [
        r["entity_id"] for r in engine.get_triage_cases(0, 10)
    ]
    assert got["data_origin"] == "engine"


def test_any_account_resolves_and_an_invented_one_does_not(port: GovernedToolPort) -> None:
    assert _ok(port, "resolve_entity", {"entity_id": "cr84920"})["entity_id"] == "CR84920"
    outcome = port.call(AML, "get_aml_dossier", {"entity_id": "CR00001"})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.NOT_FOUND


def test_metrics_for_an_alert_other_than_the_story_account_are_available(
    port: GovernedToolPort, engine: EngineAMLService
) -> None:
    other = next(
        r["entity_id"]
        for r in engine.get_triage_cases(0, 30)
        if r["entity_id"] not in {"CR84920", "CR91204"}
    )
    got = _ok(port, "get_metric", {"metric_id": "discrepancy_multiplier", "entity_id": other})
    assert got["data_origin"] == "engine" and got["value"] > 0


def test_withdrawal_risk_and_hold_proposal_follow_the_pending_withdrawal(
    port: GovernedToolPort,
) -> None:
    risk = _ok(port, "check_withdrawal_risk", {"entity_id": "CR84920"})
    assert risk["withdrawal_id"] == "W-84920-1" and risk["recommendation"] == "PROPOSE_HOLD"
    hold = _ok(port, "propose_hold", {"entity_id": "CR84920"})
    assert (
        hold["withdrawal_id"] == "W-84920-1" and hold["signed"] is False and hold["staged"] is False
    )


def test_an_account_without_a_pending_withdrawal_cannot_be_held(
    port: GovernedToolPort, engine: EngineAMLService
) -> None:
    clean = next(a for a in engine.account_ids() if engine.get_pending_withdrawal(a) is None)
    outcome = port.call(AML, "propose_hold", {"entity_id": clean})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.NOT_FOUND


def test_network_and_timeline_tools_are_computed_for_a_non_story_ring_member(
    port: GovernedToolPort, engine: EngineAMLService
) -> None:
    ring = next(r for r in engine.get_triage_cases(0, 30) if r["syndicate_size"] == 14)
    graph = _ok(port, "get_network_evidence", {"entity_id": ring["entity_id"]})
    assert graph["hub_suppressed_count"] >= 1
    timeline = _ok(port, "get_activity_timeline", {"entity_id": ring["entity_id"]})
    assert any(e["kind"] == "RING_LINK" for e in timeline["events"])
