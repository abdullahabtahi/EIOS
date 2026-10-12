"""Tests for Scenario Simulation edge cases and extrapolation warnings (T020, US3)."""

import pytest

from eios.synthesis.exceptions import ExtrapolationWarning
from eios.synthesis.models import CausalEdge, ScenarioShockSpec
from eios.synthesis.scenario import ScenarioSimulator
from eios.synthesis.scm import CausalDAG


@pytest.fixture
def multi_path_dag():
    edges = [
        CausalEdge(
            source_metric="driver_1",
            target_metric="intermediate",
            weight=2.0,
            ci_lower=1.8,
            ci_upper=2.2,
            confidence=0.9,
            rationale="",
        ),
        CausalEdge(
            source_metric="driver_2",
            target_metric="intermediate",
            weight=3.0,
            ci_lower=2.7,
            ci_upper=3.3,
            confidence=0.9,
            rationale="",
        ),
        CausalEdge(
            source_metric="intermediate",
            target_metric="outcome",
            weight=10.0,
            ci_lower=9.0,
            ci_upper=11.0,
            confidence=0.95,
            rationale="",
        ),
        CausalEdge(
            source_metric="unrelated_node",
            target_metric="other_node",
            weight=5.0,
            ci_lower=4.0,
            ci_upper=6.0,
            confidence=0.8,
            rationale="",
        ),
    ]
    return CausalDAG(edges=edges)


def test_multi_shock_additive_propagation(multi_path_dag):
    """Verify simultaneous shocks combine additively in downstream metrics."""
    simulator = ScenarioSimulator(dag=multi_path_dag)
    spec = ScenarioShockSpec(
        scenario_name="Multi-Shock Test",
        shocks={"driver_1": 2.0, "driver_2": 4.0},
    )
    res = simulator.simulate(spec)

    # intermediate = 2.0 * 2.0 + 4.0 * 3.0 = 4.0 + 12.0 = 16.0
    # outcome = 16.0 * 10.0 = 160.0
    assert res.propagated_deltas["intermediate"] == 16.0
    assert res.propagated_deltas["outcome"] == 160.0


def test_unlinked_metrics_receive_zero_delta(multi_path_dag):
    """Verify shocked nodes do not perturb disconnected DAG components."""
    simulator = ScenarioSimulator(dag=multi_path_dag)
    spec = ScenarioShockSpec(
        scenario_name="Unlinked Shock Test",
        shocks={"unrelated_node": 10.0},
    )
    res = simulator.simulate(spec)

    assert res.propagated_deltas["other_node"] == 50.0
    assert "outcome" not in res.propagated_deltas or res.propagated_deltas["outcome"] == 0.0


def test_extreme_shock_raises_extrapolation_warning(multi_path_dag):
    """Verify extreme shocks (> 3.0 magnitude) trigger ExtrapolationWarning."""
    simulator = ScenarioSimulator(dag=multi_path_dag)
    spec = ScenarioShockSpec(
        scenario_name="Extreme Shock",
        shocks={"driver_1": 15.0},  # Extreme outlier shock
    )
    with pytest.warns(ExtrapolationWarning, match="outlier shock"):
        res = simulator.simulate(spec)

    # Asserts non-linear confidence interval expansion
    ci = res.confidence_intervals["outcome"]
    width = ci[1] - ci[0]
    expected_nominal_width = abs(res.propagated_deltas["outcome"]) * 0.3
    assert width > expected_nominal_width
