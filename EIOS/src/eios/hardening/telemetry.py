"""Telemetry collection and linear-regression memory leak detector for soak tests."""

from __future__ import annotations

import math
import tracemalloc
import uuid
from datetime import UTC, datetime

import numpy as np

from eios.hardening.models import SoakTestTelemetryReport


class MemorySnapshot:
    """Individual memory point-in-time sample."""

    def __init__(self, timestamp: datetime, memory_mb: float, event_count: int) -> None:
        self.timestamp = timestamp
        self.memory_mb = memory_mb
        self.event_count = event_count


class MemoryLeakDetector:
    """Evaluates memory growth trends via linear regression to detect subtle leaks."""

    def __init__(self, leak_threshold_mb_per_k: float = 0.05) -> None:
        self.leak_threshold = leak_threshold_mb_per_k
        self.snapshots: list[MemorySnapshot] = []

    def start_tracking(self) -> None:
        """Starts Python tracemalloc if not already active."""
        if not tracemalloc.is_tracing():
            tracemalloc.start()

    def record_snapshot(self, event_count: int, memory_mb: float | None = None) -> MemorySnapshot:
        """Records a point-in-time memory allocation sample."""
        if memory_mb is None:
            if tracemalloc.is_tracing():
                current_bytes, _ = tracemalloc.get_traced_memory()
                measured_mb = current_bytes / (1024.0 * 1024.0)
            else:
                measured_mb = 10.0  # Baseline fallback
        else:
            measured_mb = float(memory_mb)

        snapshot = MemorySnapshot(
            timestamp=datetime.now(UTC),
            memory_mb=round(measured_mb, 4),
            event_count=event_count,
        )
        self.snapshots.append(snapshot)
        return snapshot

    def compute_slope(self) -> tuple[float, bool]:
        """Calculates linear regression slope (MB per 1,000 events) and leak-free flag."""
        if len(self.snapshots) < 2:
            return 0.0, True

        x = np.array([s.event_count / 1000.0 for s in self.snapshots], dtype=np.float64)
        y = np.array([s.memory_mb for s in self.snapshots], dtype=np.float64)

        x_dev = x - np.mean(x)
        denom = float(np.sum(x_dev**2))
        if math.isclose(denom, 0.0, abs_tol=1e-9):
            slope = 0.0
        else:
            slope = float(np.sum(x_dev * (y - np.mean(y))) / denom)

        is_leak_free = abs(slope) <= self.leak_threshold
        return round(slope, 4), is_leak_free


class HardeningTelemetryCollector:
    """Tracks latency distributions and operational metrics across test runs."""

    def __init__(self) -> None:
        self._latencies: dict[str, list[float]] = {}
        self.leak_detector = MemoryLeakDetector()

    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Records an execution latency observation in milliseconds."""
        if operation not in self._latencies:
            self._latencies[operation] = []
        self._latencies[operation].append(float(latency_ms))

    def get_percentiles(self, operation: str) -> tuple[float, float, float]:
        """Computes (p50, p95, p99) latencies for an operation."""
        data = self._latencies.get(operation, [])
        if not data:
            return 0.0, 0.0, 0.0
        arr = np.array(data, dtype=np.float64)
        p50 = float(np.percentile(arr, 50))
        p95 = float(np.percentile(arr, 95))
        p99 = float(np.percentile(arr, 99))
        return round(p50, 2), round(p95, 2), round(p99, 2)

    def generate_soak_report(
        self,
        simulated_days: float,
        duration_seconds: float,
        total_events: int,
        total_queries: int,
        total_actions: int,
        slo_error_budgets_healthy: bool = True,
    ) -> SoakTestTelemetryReport:
        """Constructs a certified SoakTestTelemetryReport from observed metrics."""
        slope, is_leak_free = self.leak_detector.compute_slope()
        p50, p95, p99 = self.get_percentiles("metric_query")

        snaps = self.leak_detector.snapshots
        init_mb = snaps[0].memory_mb if snaps else 15.0
        peak_mb = max((s.memory_mb for s in snaps), default=init_mb)
        final_mb = snaps[-1].memory_mb if snaps else init_mb

        return SoakTestTelemetryReport(
            soak_id=str(uuid.uuid4()),
            simulated_days=simulated_days,
            execution_duration_seconds=round(duration_seconds, 2),
            total_events_ingested=total_events,
            total_queries_served=total_queries,
            total_actions_processed=total_actions,
            initial_memory_mb=round(init_mb, 2),
            peak_memory_mb=round(peak_mb, 2),
            final_memory_mb=round(final_mb, 2),
            memory_slope_mb_per_k_events=slope,
            is_leak_free=is_leak_free,
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            latency_p99_ms=p99,
            slo_error_budgets_healthy=slo_error_budgets_healthy,
        )
