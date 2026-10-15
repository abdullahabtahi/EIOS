"""The executive plane is computed and measured against what was planted (spec 034 SC-001 to SC-005)."""

from typing import Any

import pytest

from eios.dataplane.executive_scenario import UnsupportedShockError
from eios.dataplane.executive_service import UNVERIFIED, VERIFIED, EngineExecutiveService
from eios.foundry.scenarios.executive_world import PAYOUT
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import DataOrigin, ToolErrorCode
from eios.ontology.omcp.port.principal import principal_for
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.service import GovernedToolPort

SHOCK = "competitor_payout_increase"
RL6_MS = 200.0  # RL-6
EXEC = principal_for("uid-test", "executive")


def test_the_fit_recovers_the_planted_chain_and_rejects_the_control(
    executive_service: EngineExecutiveService,
) -> None:
    q = executive_service.snapshot.quality
    assert q.chain_edges_passed == q.chain_edges == 3
    assert q.control_rejected
    assert q.max_coefficient_error < 0.10  # [ASSUMPTION] tolerance on a two-year fit


def test_the_forecast_beats_persistence_with_a_measured_interval(
    executive_service: EngineExecutiveService,
) -> None:
    view = executive_service.get_forecast("net_revenue_usd")
    assert view.skill_vs_persistence is not None and view.skill_vs_persistence < 1.0
    assert view.interval_low < view.point_estimate < view.interval_high  # type: ignore[operator]
    assert view.interval_coverage is not None and view.interval_coverage >= 0.70
    with pytest.raises(KeyError):
        executive_service.get_forecast("churn_hazard_probability")


def test_the_briefing_is_contract_valid_and_every_horizon_is_computed(
    executive_service: EngineExecutiveService,
) -> None:
    b = executive_service.get_morning_briefing()
    contract = b.to_contract_dict()  # validated against the schema
    assert [h["horizon_name"] for h in contract["horizons"]] == [
        "Competitive",
        "Partner",
        "Client",
        "Financial",
    ]
    financial = next(h for h in b.horizons if h.horizon_name == "Financial")
    forecast = executive_service.get_forecast("net_revenue_usd")
    assert financial.observed_value == round(forecast.point_estimate, 2)
    assert b.risks and b.opportunities
    assert not any("18 bps" in h.headline or "68%" in h.headline for h in b.horizons)


def test_the_graph_labels_the_control_correlation_only(
    executive_service: EngineExecutiveService,
) -> None:
    dag = executive_service.get_causal_dag()
    dag.to_contract_dict()
    labels = {(e.source_node_id, e.target_node_id): e.refuter.status_label for e in dag.edges}
    assert labels[("avg_spread_pip", "partner_churn_rate")] == UNVERIFIED
    assert [v for k, v in labels.items() if k[0] != "avg_spread_pip"] == [VERIFIED] * 3


@pytest.mark.parametrize("magnitude", [-20.0, -1.0, 0.0, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0])
def test_what_if_meets_rl6_and_closes_to_one_hundred(
    executive_service: EngineExecutiveService, magnitude: float
) -> None:
    out = executive_service.simulate_what_if_shock(SHOCK, magnitude)
    assert out["latency_ms"] < RL6_MS
    assert out["attribution_sum_pct"] == 100.0
    assert sum(a["contribution_pct"] for a in out["attribution_waterfall"]) == pytest.approx(100.0)
    low, high = sorted(out["confidence_interval"])
    assert low <= out["projected_changes"]["projected_revenue_impact_usd"] <= high


def test_what_if_effect_matches_the_planted_chain(
    executive_service: EngineExecutiveService,
) -> None:
    truth = executive_service.snapshot.world.truth
    step = executive_service.snapshot.latest[PAYOUT] * 0.10
    expected = step * truth.payout_to_churn * truth.churn_to_ftd * truth.ftd_to_revenue
    got = executive_service.simulate_what_if_shock(SHOCK, 10.0)["projected_changes"]
    assert got["projected_revenue_impact_usd"] == pytest.approx(expected, rel=0.10)
    assert got["partner_churn_delta_pct"] > 0 > got["first_deposit_delta_pct"]


def test_mitigations_exist_only_for_a_loss_and_never_exceed_it(
    executive_service: EngineExecutiveService,
) -> None:
    loss = executive_service.simulate_what_if_shock(SHOCK, 10.0)
    assert loss["mitigations"]
    for m in loss["mitigations"]:
        assert (
            0
            < m["projected_margin_kept_usd"]
            <= -loss["projected_changes"]["projected_revenue_impact_usd"]
        )
    margins = [m["projected_margin_kept_usd"] for m in loss["mitigations"]]
    assert margins == sorted(margins, reverse=True)
    assert executive_service.simulate_what_if_shock(SHOCK, -10.0)["mitigations"] == []
    assert executive_service.simulate_what_if_shock(SHOCK, 0.0)["mitigations"] == []


def test_a_shock_beyond_the_history_says_so(executive_service: EngineExecutiveService) -> None:
    assert (
        executive_service.simulate_what_if_shock(SHOCK, 5.0)["extrapolates_beyond_history"] is False
    )
    assert (
        executive_service.simulate_what_if_shock(SHOCK, 100.0)["extrapolates_beyond_history"]
        is True
    )


def test_a_shock_with_no_tested_path_is_refused(executive_service: EngineExecutiveService) -> None:
    with pytest.raises(UnsupportedShockError):
        executive_service.simulate_what_if_shock("competitor_spread_cut", 10.0)


# --- the tool port on the engine plane -----------------------------------------------------------------------


@pytest.fixture(scope="module")
def port(executive_service: EngineExecutiveService, partner_service: Any) -> GovernedToolPort:
    from eios.cockpit.aml import AMLWorkstationService

    return build_port(
        ReadModels.over(
            AMLWorkstationService(), partner=partner_service, executive=executive_service
        )
    )


def _ok(port: GovernedToolPort, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    outcome = port.call(EXEC, tool, args)
    assert outcome.error is None, outcome.error
    return outcome.payload()


def test_tools_carry_the_engine_origin_and_equal_the_screen(
    port: GovernedToolPort, executive_service: EngineExecutiveService
) -> None:
    screen = executive_service.get_morning_briefing()
    got = _ok(port, "get_briefing", {})
    assert got["data_origin"] == DataOrigin.ENGINE.value
    assert [h["observed_value"] for h in got["horizons"]] == [
        h.observed_value for h in screen.horizons
    ]
    fc = _ok(port, "get_forecast", {"metric_id": "net_revenue_usd"})
    assert fc["interval_low"] < fc["point_estimate"] < fc["interval_high"]
    assert fc["skill_vs_persistence"] < 1.0 and fc["data_origin"] == DataOrigin.ENGINE.value


def test_what_if_tool_labels_causality_and_refuses_the_spread_shock(port: GovernedToolPort) -> None:
    got = _ok(port, "run_what_if", {"shock": SHOCK, "magnitude_pct": 8.0})
    assert got["causal_label"] == "VERIFIED_CAUSAL" and got["mitigations"]
    assert got["extrapolates_beyond_history"] is False
    wide = _ok(port, "run_what_if", {"shock": SHOCK, "magnitude_pct": 100.0})
    assert (
        wide["causal_label"] == "CORRELATION_ONLY" and wide["extrapolates_beyond_history"] is True
    )
    refused = port.call(
        EXEC, "run_what_if", {"shock": "competitor_spread_cut", "magnitude_pct": 5.0}
    )
    assert refused.error is not None and refused.error.code is ToolErrorCode.DATA_UNAVAILABLE


def test_portfolio_net_revenue_is_the_current_value_not_the_projection(
    port: GovernedToolPort, executive_service: EngineExecutiveService
) -> None:
    got = _ok(port, "get_metric", {"metric_id": "net_revenue_usd"})
    assert got["value"] == executive_service.current_net_revenue()
    assert got["data_origin"] == DataOrigin.ENGINE.value
