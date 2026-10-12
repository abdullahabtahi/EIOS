"""Tests for High-Resolution Turn Latency Tracker (T048)."""

import time

from eios.evals.latency import LatencyTracker, measure_turn_latency


def test_measure_turn_latency():
    with measure_turn_latency() as timer:
        time.sleep(0.01)  # 10ms
        timer.record_first_token()
        time.sleep(0.01)

    assert timer.first_token_latency_ms >= 8.0
    assert timer.total_latency_ms >= 18.0
    assert timer.first_token_latency_ms <= timer.total_latency_ms


def test_latency_tracker_percentiles():
    tracker = LatencyTracker(sla_first_token_ms=3000.0, sla_total_ms=20000.0)
    for ms in [100.0, 150.0, 200.0, 300.0, 500.0, 1000.0]:
        tracker.record(first_token_ms=ms * 0.2, total_ms=ms)

    metrics = tracker.compute_summary()
    assert "p50_total_ms" in metrics
    assert "p95_total_ms" in metrics
    assert "max_total_ms" in metrics
    assert metrics["sla_met"] is True
    assert metrics["max_total_ms"] == 1000.0
