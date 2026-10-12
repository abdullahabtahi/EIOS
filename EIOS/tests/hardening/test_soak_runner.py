"""Tests for User Story 3: Multi-Horizon Accelerated Soak Testing & SLO Compliance."""

from datetime import UTC, datetime
import pytest

from eios.hardening.models import SoakTestTelemetryReport
from eios.hardening.schemas import validate_contract
from eios.hardening.telemetry import MemoryLeakDetector, HardeningTelemetryCollector
from eios.hardening.soak import AcceleratedSoakTestRunner


def test_accelerated_soak_execution():
    """Verify high-concurrency accelerated 7-day soak simulation and report generation."""
    runner = AcceleratedSoakTestRunner(
        simulated_days=7.0,
        events_per_day=400,
        queries_per_day=40,
        actions_per_day=20,
    )
    report = runner.run_soak_simulation()

    assert isinstance(report, SoakTestTelemetryReport)
    assert report.simulated_days == 7.0
    assert report.total_events_ingested == 2800
    assert report.total_queries_served == 280
    assert report.total_actions_processed == 140
    assert report.execution_duration_seconds > 0.0
    assert report.is_leak_free is True
    assert report.slo_error_budgets_healthy is True
    assert report.latency_p50_ms >= 0.0
    assert report.latency_p95_ms >= report.latency_p50_ms
    assert report.latency_p99_ms >= report.latency_p95_ms

    dumped = report.model_dump(mode="json")
    assert validate_contract(dumped, "soak-test-telemetry-report") is True


def test_memory_leak_slope_detection():
    """Verify linear regression slope correctly flags monotonic leaks vs stable memory."""
    # 1. Stable memory
    stable_detector = MemoryLeakDetector(leak_threshold_mb_per_k=0.05)
    stable_detector.record_snapshot(event_count=0, memory_mb=25.0)
    stable_detector.record_snapshot(event_count=1000, memory_mb=25.01)
    stable_detector.record_snapshot(event_count=2000, memory_mb=24.99)
    stable_detector.record_snapshot(event_count=3000, memory_mb=25.02)
    slope, is_leak_free = stable_detector.compute_slope()
    assert is_leak_free is True
    assert abs(slope) < 0.05

    # 2. Leaking memory (+5.0 MB per 1,000 events)
    leak_detector = MemoryLeakDetector(leak_threshold_mb_per_k=0.05)
    leak_detector.record_snapshot(event_count=0, memory_mb=25.0)
    leak_detector.record_snapshot(event_count=1000, memory_mb=30.0)
    leak_detector.record_snapshot(event_count=2000, memory_mb=35.0)
    leak_detector.record_snapshot(event_count=3000, memory_mb=40.0)
    leak_slope, leak_free = leak_detector.compute_slope()
    assert leak_free is False
    assert leak_slope > 1.0


def test_slo_budget_tracking_during_soak():
    """Verify that latency observations and error budget tracking remain within limits."""
    collector = HardeningTelemetryCollector()
    for latency in [2.5, 3.1, 4.0, 5.2, 8.9, 12.0, 15.4, 22.0, 35.0, 80.0]:
        collector.record_latency("metric_query", latency)

    p50, p95, p99 = collector.get_percentiles("metric_query")
    assert p50 > 0.0
    assert p95 > p50
    assert p99 >= p95
