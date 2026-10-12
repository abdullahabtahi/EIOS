"""Tests for Additive Driver Attribution Engine (T015, US2)."""

import pytest

from eios.synthesis.attribution import DriverAttributionEngine
from eios.synthesis.models import CausalEdge
from eios.synthesis.scm import CausalDAG


@pytest.fixture
def test_dag():
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
            source_metric="platform_latency_ms",
            target_metric="ftd_count_28d",
            weight=-0.8,
            ci_lower=-1.2,
            ci_upper=-0.4,
            confidence=0.85,
            rationale="Operations latency",
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
    return CausalDAG(edges=edges)


def test_driver_attribution_strictly_sums_to_100_percent(test_dag):
    """Verify that driver attribution percentages sum strictly to 100.0%."""
    engine = DriverAttributionEngine(dag=test_dag)

    # Driver changes: competitor moved, latency spiked, partner churned
    driver_deltas = {
        "competitor_payout_rate": 0.15,
        "partner_churn_rate": 0.05,
        "platform_latency_ms": 120.0,
    }

    attribution_list = engine.attribute_drivers(
        outcome_metric="net_deposit_volume_usd",
        driver_deltas=driver_deltas,
    )

    assert len(attribution_list) == 3
    total_pct = sum(item.percentage for item in attribution_list)

    # Strict invariant: exactly 100.0%
    assert abs(total_pct - 100.0) < 0.001

    # Check that highest driver is competitor_payout_rate or partner_churn_rate
    top_driver = max(attribution_list, key=lambda x: x.percentage)
    assert top_driver.percentage > 30.0
    assert top_driver.direction in ["POSITIVE", "NEGATIVE"]


def test_driver_attribution_zero_delta_fallback(test_dag):
    """Verify zero-delta fallback produces balanced equal distribution summing to 100.0%."""
    engine = DriverAttributionEngine(dag=test_dag)

    zero_deltas = {
        "competitor_payout_rate": 0.0,
        "partner_churn_rate": 0.0,
        "platform_latency_ms": 0.0,
    }

    attribution_list = engine.attribute_drivers(
        outcome_metric="net_deposit_volume_usd",
        driver_deltas=zero_deltas,
    )

    assert len(attribution_list) == 3
    total_pct = sum(item.percentage for item in attribution_list)
    assert abs(total_pct - 100.0) < 0.001

    for item in attribution_list:
        assert item.percentage == pytest.approx(33.33, abs=0.1)


def test_driver_attribution_unlinked_drivers_handled(test_dag):
    """Verify that unlinked drivers (no path to outcome) receive 0 impact."""
    engine = DriverAttributionEngine(dag=test_dag)

    deltas = {
        "competitor_payout_rate": 0.10,
        "unlinked_driver": 500.0,
    }

    attribution_list = engine.attribute_drivers(
        outcome_metric="net_deposit_volume_usd",
        driver_deltas=deltas,
    )

    unlinked = next(x for x in attribution_list if x.driver_metric == "unlinked_driver")
    assert unlinked.absolute_impact == 0.0
    assert unlinked.percentage == 0.0

    total_pct = sum(item.percentage for item in attribution_list)
    assert abs(total_pct - 100.0) < 0.001
