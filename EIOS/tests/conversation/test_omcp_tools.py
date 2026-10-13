"""Tests for OMCP analytical tools wrapping DuckDB, AML, and Causal DAG engines (F018, T009)."""

import pytest

from eios.conversation.tools import (
    get_governed_metric,
    inspect_aml_entity,
    inspect_partner_churn,
    query_graph_topology,
    run_causal_what_if,
)


def test_get_governed_metric():
    res = get_governed_metric(metric_id="net_deposit_volume_30d_usd", entity_id="P-882")
    assert "metric_id" in res
    assert res["metric_id"] == "net_deposit_volume_30d_usd"
    assert "value" in res
    assert isinstance(res["value"], (int, float))
    assert res["steward"] == "FinancialOperationsSteward"


def test_inspect_aml_entity():
    res = inspect_aml_entity(entity_id="CR84920")
    assert res["entity_id"] == "CR84920"
    assert res["discrepancy_multiplier"] == 16.0
    assert res["net_deposit_volume_30d_usd"] == 8000.0
    assert "kyc_declared_monthly_income_usd" in res


def test_query_graph_topology_hub_suppression():
    """Graph traversal must enforce hub suppression for high-degree nodes (k > 100)."""
    res = query_graph_topology(entity_id="CR84920", hub_threshold=100)
    assert "nodes" in res
    assert "edges" in res
    assert "hub_suppressed_count" in res
    assert isinstance(res["hub_suppressed_count"], int)


def test_inspect_partner_churn():
    res = inspect_partner_churn(partner_id="AP-1029")
    assert res["partner_id"] == "AP-1029"
    assert "churn_hazard_probability" in res
    assert res["primary_root_cause"] == "CompetitorSpreadDecay"


def test_run_causal_what_if():
    res = run_causal_what_if(shock_param="competitor_spread_delta_bps", magnitude_pct=20.0)
    assert "deltas" in res
    assert "confidence_interval_95" in res
    # Principle III: no placebo refuter ran, so no pass may be claimed; this is correlation only.
    assert res["refuter_passed"] is None
    assert res["placebo_p_value"] is None
    assert res["causal_status"] == "CORRELATION_ONLY"


def test_unknown_metric_is_an_error_not_an_invented_number():
    with pytest.raises(ValueError, match="unknown governed metric"):
        get_governed_metric(metric_id="made_up_metric")


def test_unknown_entity_for_a_known_metric_is_an_error_not_the_portfolio_default():
    with pytest.raises(ValueError, match="no governed value"):
        get_governed_metric(metric_id="net_revenue_usd", entity_id="P-999")


def test_portfolio_level_metric_without_an_entity_still_resolves():
    assert get_governed_metric(metric_id="net_revenue_usd")["value"] == 3820000.0


def test_every_fixture_tool_labels_its_origin():
    outputs = [
        get_governed_metric(metric_id="net_revenue_usd"),
        inspect_aml_entity(entity_id="CR84920"),
        query_graph_topology(entity_id="CR84920"),
        inspect_partner_churn(partner_id="AP-1029"),
        run_causal_what_if(shock_param="competitor_spread_delta_bps", magnitude_pct=20.0),
    ]
    assert all("ILLUSTRATIVE" in out["data_origin"] for out in outputs)
