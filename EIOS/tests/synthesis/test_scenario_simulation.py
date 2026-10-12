"""Tests for Parametric Scenario Simulation Engine (T019, US3)."""

from eios.synthesis.models import CausalEdge, ScenarioShockSpec
from eios.synthesis.scenario import ScenarioSimulator
from eios.synthesis.scm import CausalDAG


def test_scenario_propagation_and_mitigation_ranking():
    """Verify topological shock propagation, confidence intervals, and ranked mitigations."""
    edges = [
        CausalEdge(
            source_metric="competitor_payout_rate",
            target_metric="partner_churn_rate",
            weight=0.45,
            ci_lower=0.38,
            ci_upper=0.52,
            confidence=0.92,
            rationale="Competitor moves",
        ),
        CausalEdge(
            source_metric="partner_churn_rate",
            target_metric="ftd_count_28d",
            weight=-340.0,
            ci_lower=-410.0,
            ci_upper=-270.0,
            confidence=0.89,
            rationale="Partner churn",
        ),
        CausalEdge(
            source_metric="ftd_count_28d",
            target_metric="net_deposit_volume_usd",
            weight=45.0,
            ci_lower=38.5,
            ci_upper=51.5,
            confidence=0.95,
            rationale="Client deposits",
        ),
    ]
    dag = CausalDAG(edges=edges)
    simulator = ScenarioSimulator(dag=dag)

    shock_spec = ScenarioShockSpec(
        scenario_name="Competitor Payout Aggression",
        shocks={"competitor_payout_rate": 0.15},
        duration_days=28,
        assumptions=["Linear causal elasticity"],
    )

    result = simulator.simulate(shock_spec)

    assert result.scenario_name == "Competitor Payout Aggression"
    deltas = result.propagated_deltas

    # Verify exact directional and mathematical propagation
    assert deltas["competitor_payout_rate"] == 0.15
    assert deltas["partner_churn_rate"] == 0.0675
    assert deltas["ftd_count_28d"] == -22.95
    assert deltas["net_deposit_volume_usd"] == -1032.75

    # Verify confidence intervals
    ci = result.confidence_intervals["net_deposit_volume_usd"]
    assert ci[0] <= -1032.75 <= ci[1]

    # Verify mitigation options are ranked by ROI
    assert len(result.mitigation_options) >= 2
    top_option = result.mitigation_options[0]
    assert top_option.roi_ratio >= result.mitigation_options[1].roi_ratio
    assert top_option.action_type in [
        "AdjustPartnerTier",
        "ReviewSpreadPricing",
        "LaunchRetentionCampaign",
    ]

    # Verify performance SLA (< 200ms)
    assert result.execution_time_ms < 200.0

    # Verify assumptions list includes custom and base assumptions
    assert "Linear causal elasticity" in result.assumptions_applied
