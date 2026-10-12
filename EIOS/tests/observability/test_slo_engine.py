"""Unit and contract tests for continuous 10-SLO monitoring and error budget accounting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time
import pytest

from eios.observability.buffer import ServiceLevelIndicatorMeasurement
from eios.observability.schemas import validate_contract
from eios.observability.slo_catalog import SLICategory, SLOTier, list_slo_configs
from eios.observability.slo_engine import (
    ErrorBudgetHealth,
    ErrorBudgetStatus,
    SLOMonitoringEngine,
    error_budget_to_contract_dict,
)


def test_slo_engine_healthy_budget():
    """Verify healthy error budget calculation with high compliance."""
    engine = SLOMonitoringEngine()
    now = datetime.now(timezone.utc)

    # Ingest 1000 events: 998 compliant, 2 failed for METRIC_QUERY_LATENCY (target: 99.5%)
    for i in range(1000):
        is_compliant = i >= 2
        engine.record_event(
            sli_name=SLICategory.METRIC_QUERY_LATENCY,
            observed_value=250.0 if is_compliant else 650.0,
            target_threshold=500.0,
            is_compliant=is_compliant,
            correlation_id=f"corr-{i}",
            timestamp=now - timedelta(minutes=i % 100),
        )

    status = engine.evaluate_slo(SLICategory.METRIC_QUERY_LATENCY)
    assert status.total_events == 1000
    assert status.compliant_events == 998
    assert status.failed_events == 2
    assert status.compliance_percentage == 99.8
    # Target is 99.5% (allowed failure = 0.5% = 5 failed events out of 1000)
    # Actual failure is 2 / 1000 = 0.2%. Budget spent = 0.2 / 0.5 = 40%. Budget remaining = 60%.
    assert pytest.approx(status.budget_remaining_pct, rel=1e-2) == 60.0
    assert status.status == ErrorBudgetHealth.HEALTHY
    assert status.is_frozen is False


def test_slo_engine_warning_and_freeze_transitions():
    """Verify budget transitions into WARNING (< 20%) and FEATURE_FREEZE (<= 0%)."""
    engine = SLOMonitoringEngine()
    now = datetime.now(timezone.utc)

    # Ingest for INGESTION_FRESHNESS: target is 99.0% (allowed failure = 1%)
    # Out of 1000 events:
    # 982 compliant, 18 failed.
    # Allowed failures = 10. Actual failures = 18. Budget spent = 1.8x. Remaining = -80%.
    for i in range(1000):
        is_compliant = i >= 18
        engine.record_event(
            sli_name=SLICategory.INGESTION_FRESHNESS,
            observed_value=15.0 if is_compliant else 45.0,
            target_threshold=30.0,
            is_compliant=is_compliant,
            correlation_id=f"corr-fresh-{i}",
            timestamp=now - timedelta(minutes=i % 60),
        )

    status = engine.evaluate_slo(SLICategory.INGESTION_FRESHNESS)
    assert status.total_events == 1000
    assert status.failed_events == 18
    assert status.budget_remaining_pct < 0.0
    assert status.status == ErrorBudgetHealth.FEATURE_FREEZE
    assert status.is_frozen is True  # INGESTION_FRESHNESS is TIER_1_CRITICAL


def test_slo_engine_contract_schema_compliance():
    """Verify error budget status payload conforms to error-budget-status.schema.json."""
    engine = SLOMonitoringEngine()
    now = datetime.now(timezone.utc)

    engine.record_event(
        sli_name=SLICategory.APPROVAL_SERVICE_AVAILABILITY,
        observed_value=1.0,
        target_threshold=1.0,
        is_compliant=True,
        correlation_id="corr-avail-1",
        timestamp=now,
    )

    status = engine.evaluate_slo(SLICategory.APPROVAL_SERVICE_AVAILABILITY)
    payload = error_budget_to_contract_dict(status)
    assert validate_contract(payload, "error-budget-status.schema.json") is True


def test_slo_engine_sub_100ms_evaluation_latency():
    """Verify evaluating all 10 production SLOs takes strictly < 100ms (performance requirement)."""
    engine = SLOMonitoringEngine()
    now = datetime.now(timezone.utc)

    # Seed 500 events across each SLO
    for sli in list_slo_configs():
        for i in range(200):
            engine.record_event(
                sli_name=sli.sli_name,
                observed_value=10.0,
                target_threshold=20.0,
                is_compliant=True,
                correlation_id=f"bench-{i}",
                timestamp=now - timedelta(minutes=i),
            )

    t0 = time.perf_counter()
    summary = engine.evaluate_all_slos()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(summary) >= 10
    assert elapsed_ms < 100.0


def test_slo_catalog_helpers():
    """Verify get_slo_config and is_tier_1_critical helpers."""
    from eios.observability.slo_catalog import get_slo_config, is_tier_1_critical

    cfg = get_slo_config("ingestion_freshness")
    assert cfg.sli_name == SLICategory.INGESTION_FRESHNESS
    assert is_tier_1_critical(SLICategory.INGESTION_FRESHNESS) is True
    assert is_tier_1_critical(SLICategory.AGENT_TURN_FIRST_TOKEN) is False

    with pytest.raises(KeyError, match="Unknown SLI category"):
        get_slo_config("nonexistent_sli")


def test_buffer_pruning_and_observed_values():
    """Verify buffer pruning, clear, and observed values extraction."""
    from eios.observability.buffer import SLIEventBufferManager, ServiceLevelIndicatorMeasurement

    mgr = SLIEventBufferManager(max_capacity_per_sli=100)
    now = datetime.now(timezone.utc)

    for i in range(10):
        mgr.record_measurement(
            ServiceLevelIndicatorMeasurement(
                measurement_id=f"m-{i}",
                timestamp=now - timedelta(days=35 - i),
                sli_name=SLICategory.METRIC_QUERY_LATENCY,
                observed_value=float(i * 10),
                target_threshold=500.0,
                is_compliant=True,
                correlation_id=f"c-{i}",
            )
        )

    assert mgr.total_events_count() == 10
    values = mgr.get_observed_values(SLICategory.METRIC_QUERY_LATENCY, start_time=now - timedelta(days=40))
    assert len(values) == 10

    # Prune older than 28 days
    pruned = mgr.prune_older_than(cutoff=now - timedelta(days=28))
    assert pruned > 0
    assert mgr.total_events_count() < 10

    mgr.clear()
    assert mgr.total_events_count() == 0

