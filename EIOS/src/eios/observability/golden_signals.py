"""Four Golden Signals Health Telemetry Collector and Aggregator.

Calculates Traffic (req/s), Latency percentiles (p50, p90, p95, p99), Error Rate (%),
and Resource Saturation (%) across all core platform services with saturation warning flags.
"""

from __future__ import annotations

import math
import threading
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

CORE_PLATFORM_SERVICES = [
    "omcp_server",
    "reasoning_coordinator",
    "hot_state_engine",
    "ledger_sequencer",
    "approval_service",
    "cockpit_gateway",
]


class ServiceGoldenSignals(BaseModel):
    """Standardized Four Golden Signals exported across platform services."""

    service_name: str = Field(..., description="Microservice name")
    timestamp: datetime = Field(..., description="Sampling timestamp in UTC")
    requests_per_second: float = Field(..., ge=0.0, description="Throughput in requests per second")
    latency_p50_ms: float = Field(..., ge=0.0, description="50th percentile latency in ms")
    latency_p90_ms: float = Field(..., ge=0.0, description="90th percentile latency in ms")
    latency_p95_ms: float = Field(..., ge=0.0, description="95th percentile latency in ms")
    latency_p99_ms: float = Field(..., ge=0.0, description="99th percentile latency in ms")
    error_rate_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Error percentage of total requests"
    )
    saturation_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Resource saturation percentage"
    )
    is_saturated: bool = Field(default=False, description="True if saturation exceeds 85.0%")


class _RequestEntry:
    __slots__ = ("timestamp", "latency_ms", "is_error")

    def __init__(self, timestamp: datetime, latency_ms: float, is_error: bool) -> None:
        self.timestamp = timestamp
        self.latency_ms = latency_ms
        self.is_error = is_error


def _compute_percentile(sorted_values: list[float], percentile: float) -> float:
    """Computes percentile from a pre-sorted list using nearest-rank / linear interpolation."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]

    rank = (percentile / 100.0) * (n - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return sorted_values[lower]
    weight = rank - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


class GoldenSignalsCollector:
    """Collects and aggregates Four Golden Signals across platform services."""

    def __init__(self, buffer_maxlen_per_service: int = 50_000) -> None:
        self.buffer_maxlen = buffer_maxlen_per_service
        self._buffers: dict[str, deque[_RequestEntry]] = {}
        self._saturation: dict[str, float] = {}
        self._lock = threading.RLock()

    def record_request(
        self,
        service_name: str,
        latency_ms: float,
        is_error: bool = False,
        timestamp: datetime | None = None,
    ) -> None:
        """Records a single service request observation."""
        ts = timestamp or datetime.now(UTC)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        with self._lock:
            if service_name not in self._buffers:
                self._buffers[service_name] = deque(maxlen=self.buffer_maxlen)
            self._buffers[service_name].append(_RequestEntry(ts, max(0.0, latency_ms), is_error))

    def set_saturation(self, service_name: str, saturation_pct: float) -> None:
        """Updates the resource saturation percentage for a service."""
        with self._lock:
            self._saturation[service_name] = max(0.0, min(100.0, saturation_pct))

    def get_golden_signals(
        self,
        service_name: str,
        window_seconds: int = 60,
        reference_time: datetime | None = None,
    ) -> ServiceGoldenSignals:
        """Computes Four Golden Signals for a given service over a sliding time window."""
        ref_time = reference_time or datetime.now(UTC)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=UTC)

        cutoff = ref_time - timedelta(seconds=window_seconds)

        with self._lock:
            buf = self._buffers.get(service_name)
            entries: list[_RequestEntry] = []
            if buf:
                for entry in buf:
                    if entry.timestamp >= cutoff:
                        if entry.timestamp <= ref_time:
                            entries.append(entry)

            saturation_pct = self._saturation.get(service_name, 0.0)

        total_reqs = len(entries)
        rps = total_reqs / max(1, window_seconds)

        if total_reqs == 0:
            return ServiceGoldenSignals(
                service_name=service_name,
                timestamp=ref_time,
                requests_per_second=0.0,
                latency_p50_ms=0.0,
                latency_p90_ms=0.0,
                latency_p95_ms=0.0,
                latency_p99_ms=0.0,
                error_rate_pct=0.0,
                saturation_pct=round(saturation_pct, 2),
                is_saturated=(saturation_pct > 85.0),
            )

        error_count = sum(1 for e in entries if e.is_error)
        error_rate_pct = (error_count / total_reqs) * 100.0

        latencies = sorted(e.latency_ms for e in entries)
        p50 = _compute_percentile(latencies, 50.0)
        p90 = _compute_percentile(latencies, 90.0)
        p95 = _compute_percentile(latencies, 95.0)
        p99 = _compute_percentile(latencies, 99.0)

        return ServiceGoldenSignals(
            service_name=service_name,
            timestamp=ref_time,
            requests_per_second=round(rps, 2),
            latency_p50_ms=round(p50, 2),
            latency_p90_ms=round(p90, 2),
            latency_p95_ms=round(p95, 2),
            latency_p99_ms=round(p99, 2),
            error_rate_pct=round(error_rate_pct, 2),
            saturation_pct=round(saturation_pct, 2),
            is_saturated=(saturation_pct > 85.0),
        )

    def get_all_services_signals(
        self,
        services: list[str] | None = None,
        window_seconds: int = 60,
        reference_time: datetime | None = None,
    ) -> list[ServiceGoldenSignals]:
        """Calculates golden signals for all core platform services."""
        target_services = services or CORE_PLATFORM_SERVICES
        return [
            self.get_golden_signals(svc, window_seconds, reference_time) for svc in target_services
        ]


def golden_signals_to_contract_dict(signals: ServiceGoldenSignals) -> dict[str, Any]:
    """Converts ServiceGoldenSignals to dictionary matching contract schema."""
    return {
        "service_name": signals.service_name,
        "timestamp": signals.timestamp.isoformat(),
        "requests_per_second": signals.requests_per_second,
        "latency_p50_ms": signals.latency_p50_ms,
        "latency_p90_ms": signals.latency_p90_ms,
        "latency_p95_ms": signals.latency_p95_ms,
        "latency_p99_ms": signals.latency_p99_ms,
        "error_rate_pct": signals.error_rate_pct,
        "saturation_pct": signals.saturation_pct,
        "is_saturated": signals.is_saturated,
    }
