"""High-resolution turn latency tracking and percentile SLA aggregation (T051)."""

import time
from typing import Self

import numpy as np


class LatencyTimer:
    """Monotonic context manager measuring first-token and total turn latency."""

    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.first_token_time: float = 0.0
        self.end_time: float = 0.0
        self.first_token_latency_ms: float = 0.0
        self.total_latency_ms: float = 0.0

    def __enter__(self) -> Self:
        self.start_time = time.perf_counter()
        return self

    def record_first_token(self) -> None:
        if self.first_token_time == 0.0:
            self.first_token_time = time.perf_counter()
            self.first_token_latency_ms = (self.first_token_time - self.start_time) * 1000.0

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.end_time = time.perf_counter()
        self.total_latency_ms = (self.end_time - self.start_time) * 1000.0
        if self.first_token_latency_ms == 0.0:
            self.first_token_latency_ms = self.total_latency_ms


def measure_turn_latency() -> LatencyTimer:
    return LatencyTimer()


class LatencyTracker:
    """Aggregates turn latencies and checks percentiles against SLA thresholds."""

    def __init__(
        self,
        sla_first_token_ms: float = 3000.0,
        sla_total_ms: float = 20000.0,
    ) -> None:
        self.sla_first_token_ms = sla_first_token_ms
        self.sla_total_ms = sla_total_ms
        self.first_token_latencies: list[float] = []
        self.total_latencies: list[float] = []

    def record(self, first_token_ms: float, total_ms: float) -> None:
        self.first_token_latencies.append(float(first_token_ms))
        self.total_latencies.append(float(total_ms))

    def compute_summary(self) -> dict[str, float | bool]:
        if not self.total_latencies:
            return {
                "p50_total_ms": 0.0,
                "p95_total_ms": 0.0,
                "max_total_ms": 0.0,
                "p50_first_token_ms": 0.0,
                "p95_first_token_ms": 0.0,
                "sla_met": True,
            }

        p50_tot = float(np.percentile(self.total_latencies, 50))
        p95_tot = float(np.percentile(self.total_latencies, 95))
        max_tot = float(np.max(self.total_latencies))

        p50_ft = float(np.percentile(self.first_token_latencies, 50))
        p95_ft = float(np.percentile(self.first_token_latencies, 95))

        sla_met = (p95_ft <= self.sla_first_token_ms) and (p95_tot <= self.sla_total_ms)

        return {
            "p50_total_ms": p50_tot,
            "p95_total_ms": p95_tot,
            "max_total_ms": max_tot,
            "p50_first_token_ms": p50_ft,
            "p95_first_token_ms": p95_ft,
            "sla_met": sla_met,
        }
