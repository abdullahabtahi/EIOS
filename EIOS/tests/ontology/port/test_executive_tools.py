"""Shared and executive capabilities: governed numbers, derived figures, causal labels (spec 023 US4)."""

from typing import Any

import pytest

from eios.cockpit.executive import ExecutiveCockpitService
from eios.ontology.omcp.port.contracts import ToolErrorCode
from eios.ontology.omcp.port.principal import Principal
from eios.ontology.omcp.port.service import GovernedToolPort
from tests.ontology.port.conftest import who

EXEC = who("executive")


def _ok(
    port: GovernedToolPort, principal: Principal, tool: str, args: dict[str, Any]
) -> dict[str, Any]:
    outcome = port.call(principal, tool, args)
    assert outcome.error is None, outcome.error
    return outcome.payload()


def _err(
    port: GovernedToolPort, principal: Principal, tool: str, args: dict[str, Any]
) -> ToolErrorCode:
    outcome = port.call(principal, tool, args)
    assert outcome.error is not None, outcome.result
    return outcome.error.code


def test_metric_has_value_unit_definition_and_owner(port: GovernedToolPort) -> None:
    got = _ok(port, EXEC, "get_metric", {"metric_id": "net_revenue_usd"})
    assert got["value"] == 3820000.0 and got["units"]["value"] == "USD"
    assert got["definition_version"] and got["owner_role"] and got["formula_summary"]
    assert got["fact_ids"]["value"] == "metric.get:net_revenue_usd:value"


def test_metric_for_a_partner_equals_the_radar_and_differs_per_partner(
    port: GovernedToolPort,
) -> None:
    pm = who("partner_manager")
    a = _ok(
        port, pm, "get_metric", {"metric_id": "churn_hazard_probability", "entity_id": "PTR-882"}
    )
    b = _ok(
        port, pm, "get_metric", {"metric_id": "churn_hazard_probability", "entity_id": "PTR-104"}
    )
    assert (a["value"], b["value"]) == (0.78, 0.18)


def test_unknown_metric_is_invalid_and_missing_entity_is_refused(port: GovernedToolPort) -> None:
    assert (
        _err(port, EXEC, "get_metric", {"metric_id": "made_up"}) is ToolErrorCode.INVALID_ARGUMENTS
    )
    assert (
        _err(port, EXEC, "get_metric", {"metric_id": "churn_hazard_probability"})
        is ToolErrorCode.INVALID_ARGUMENTS
    )
    assert (
        _err(
            port,
            EXEC,
            "get_metric",
            {"metric_id": "churn_hazard_probability", "entity_id": "PTR-000"},
        )
        is ToolErrorCode.NOT_FOUND
    )


def test_a_metric_about_a_data_class_the_workstation_lacks_is_forbidden(
    port: GovernedToolPort,
) -> None:
    ops = who("data_operations")
    code = _err(
        port, ops, "get_metric", {"metric_id": "churn_hazard_probability", "entity_id": "PTR-882"}
    )
    assert code is ToolErrorCode.FORBIDDEN_MARKING
    aml = who("aml_investigator")
    code = _err(
        port, aml, "get_metric", {"metric_id": "churn_hazard_probability", "entity_id": "PTR-882"}
    )
    assert code is ToolErrorCode.FORBIDDEN_MARKING


def test_resolve_entity_gives_the_canonical_id(port: GovernedToolPort) -> None:
    got = _ok(port, who("partner_manager"), "resolve_entity", {"entity_id": "ap-1029"})
    assert (got["entity_id"], got["kind"]) == ("PTR-882", "partner")


def test_compare_facts_computes_from_resolved_facts(port: GovernedToolPort) -> None:
    pm = who("partner_manager")
    args = {
        "left_fact_id": "partner.signals:PTR-882:realized_volume_30d_usd",
        "right_fact_id": "partner.signals:PTR-104:realized_volume_30d_usd",
        "operation": "difference",
    }
    got = _ok(port, pm, "compare_facts", args)
    assert (
        got["left_value"] == 1240000.0
        and got["right_value"] == 840000.0
        and got["result"] == 400000.0
    )
    assert got["units"]["result"] == "USD" and got["operation"] == "difference"
    ratio = _ok(port, pm, "compare_facts", {**args, "operation": "ratio"})
    assert (
        ratio["result"] == pytest.approx(1240000 / 840000) and ratio["units"]["result"] == "ratio"
    )
    pct = _ok(port, pm, "compare_facts", {**args, "operation": "percent_change"})
    assert pct["result"] == pytest.approx(47.619, rel=1e-3) and pct["units"]["result"] == "percent"


def test_compare_facts_refuses_mixed_units_and_unknown_facts(port: GovernedToolPort) -> None:
    pm = who("partner_manager")
    mixed = {
        "left_fact_id": "partner.signals:PTR-882:realized_volume_30d_usd",
        "right_fact_id": "partner.signals:PTR-882:churn_hazard_probability",
        "operation": "difference",
    }
    assert _err(port, pm, "compare_facts", mixed) is ToolErrorCode.INVALID_ARGUMENTS
    bad = {**mixed, "right_fact_id": "partner.signals:PTR-882:nope"}
    assert _err(port, pm, "compare_facts", bad) is ToolErrorCode.NOT_FOUND
    free = {**mixed, "right_fact_id": "about 3 million"}
    assert _err(port, pm, "compare_facts", free) is ToolErrorCode.INVALID_ARGUMENTS


def test_compare_facts_cannot_reach_facts_outside_the_callers_scope(port: GovernedToolPort) -> None:
    ops = who("data_operations")
    args = {
        "left_fact_id": "aml.dossier:CR84920:discrepancy_multiplier",
        "right_fact_id": "aml.dossier:CR84920:composite_risk_score",
        "operation": "ratio",
    }
    assert _err(port, ops, "compare_facts", args) is ToolErrorCode.FORBIDDEN_ROLE


def test_causal_label_comes_from_the_numbers_not_the_status_text(port: GovernedToolPort) -> None:
    got = _ok(port, EXEC, "get_causal_evidence", {})
    by_pair = {(e["source_node_id"], e["target_node_id"]): e for e in got["edges"]}
    verified = by_pair[("competitor_payout_rate", "partner_churn_rate")]
    assert verified["causal_label"] == "VERIFIED_CAUSAL" and verified["placebo_p_value"] > 0.05
    weak = by_pair[("competitor_payout_rate", "net_pnl_usd")]
    assert weak["causal_label"] == "CORRELATION_ONLY" and weak["reason"]
    for e in got["edges"]:
        ok = e["placebo_p_value"] > 0.05 and e["confidence"] >= 0.80
        assert (e["causal_label"] == "VERIFIED_CAUSAL") is ok


def test_causal_evidence_unknown_node_is_not_found(port: GovernedToolPort) -> None:
    assert (
        _err(port, EXEC, "get_causal_evidence", {"source_node_id": "nope"})
        is ToolErrorCode.NOT_FOUND
    )


def test_what_if_sums_to_100_is_labelled_a_simulation_and_never_crashes(
    port: GovernedToolPort,
) -> None:
    got = _ok(port, EXEC, "run_what_if", {"shock": "competitor_spread_cut", "magnitude_pct": 20.0})
    assert got["is_simulation"] is True
    assert sum(a["contribution_pct"] for a in got["attribution"]) == pytest.approx(100.0, abs=1e-9)
    assert got["causal_label"] in {"VERIFIED_CAUSAL", "CORRELATION_ONLY"} and got["causal_reason"]
    assert (
        got["projected_ebitda_impact_usd"]
        == ExecutiveCockpitService().simulate_what_if_shock("competitor_spread_cut", 20.0)[
            "projected_changes"
        ]["projected_ebitda_impact_usd"]
    )
    assert (
        got["ebitda_interval_low_usd"]
        <= got["projected_ebitda_impact_usd"]
        <= got["ebitda_interval_high_usd"]
    )


@pytest.mark.parametrize("magnitude", [0.0, -35.5, 100.0])
def test_what_if_handles_edges_without_error(port: GovernedToolPort, magnitude: float) -> None:
    got = _ok(
        port, EXEC, "run_what_if", {"shock": "competitor_spread_cut", "magnitude_pct": magnitude}
    )
    assert sum(a["contribution_pct"] for a in got["attribution"]) == pytest.approx(100.0, abs=1e-9)


def test_what_if_rejects_out_of_range_and_unknown_shock(port: GovernedToolPort) -> None:
    assert (
        _err(port, EXEC, "run_what_if", {"shock": "competitor_spread_cut", "magnitude_pct": 900.0})
        is ToolErrorCode.INVALID_ARGUMENTS
    )
    assert (
        _err(port, EXEC, "run_what_if", {"shock": "free text", "magnitude_pct": 5.0})
        is ToolErrorCode.INVALID_ARGUMENTS
    )


def test_briefing_equals_the_screen(port: GovernedToolPort) -> None:
    screen = ExecutiveCockpitService().get_morning_briefing().to_contract_dict()
    got = _ok(port, EXEC, "get_briefing", {})
    assert [h["observed_value"] for h in got["horizons"]] == [
        h["observed_value"] for h in screen["horizons"]
    ]
    assert got["units"]["horizons[].observed_value"] == "USD"
    assert [r["exposure_usd"] for r in got["risks"]] == [r["exposure_usd"] for r in screen["risks"]]


def test_forecast_is_a_labelled_projection_without_an_invented_interval(
    port: GovernedToolPort,
) -> None:
    got = _ok(port, EXEC, "get_forecast", {"metric_id": "net_revenue_usd"})
    assert got["point_estimate"] == 3820000.0 and got["is_projection"] is True
    assert "ci_lower" not in got
    assert _err(port, EXEC, "get_forecast", {"metric_id": "ftd_count_28d"}) in {
        ToolErrorCode.DATA_UNAVAILABLE,
        ToolErrorCode.INVALID_ARGUMENTS,
    }


def test_account_metrics_come_from_the_dossier_and_are_unavailable_without_one(
    port: GovernedToolPort,
) -> None:
    aml = who("aml_investigator")
    got = _ok(
        port, aml, "get_metric", {"metric_id": "discrepancy_multiplier", "entity_id": "CR84920"}
    )
    assert got["value"] == 16.0 and got["units"]["value"] == "multiplier"
    deposits = _ok(
        port,
        aml,
        "get_metric",
        {"metric_id": "realized_deposit_volume_30d_usd", "entity_id": "CR84920"},
    )
    assert deposits["value"] == 8000.0
    code = _err(
        port, aml, "get_metric", {"metric_id": "discrepancy_multiplier", "entity_id": "CR91204"}
    )
    assert code is ToolErrorCode.DATA_UNAVAILABLE
    assert (
        _err(port, aml, "get_metric", {"metric_id": "net_revenue_usd", "entity_id": "CR84920"})
        is ToolErrorCode.INVALID_ARGUMENTS
    )
