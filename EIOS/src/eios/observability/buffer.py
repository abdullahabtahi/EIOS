"""Thread-Safe Discrete Rolling Ring Buffer for SLI Events and Telemetry.

Provides bounded, low-latency in-memory event recording partitioned by SLI category,
enabling O(1) appends, sliding window aggregations (1h, 6h, 24h, 28d), and automatic
time-based pruning without lock contention.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from eios.observability.slo_catalog import SLICategory

T = TypeVar("T")


class ServiceLevelIndicatorMeasurement(BaseModel):
    """Discrete SLI observation event."""

    measurement_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="Measurement timestamp in UTC")
    sli_name: SLICategory = Field(..., description="Measured SLI category")
    observed_value: float = Field(..., description="Observed quantitative metric value")
    target_threshold: float = Field(..., description="Configured SLA boundary threshold")
    is_compliant: bool = Field(..., description="True if within SLA, False if breached")
    correlation_id: str = Field(..., description="Request or transaction correlation ID")
    service_name: str | None = Field(None, description="Emitting service name")
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Additional context attributes"
    )


class TimestampedItem(Generic[T]):
    """Wrapper holding an item and its UTC timestamp."""

    __slots__ = ("item", "timestamp")

    def __init__(self, item: T, timestamp: datetime) -> None:
        if timestamp.tzinfo is None:
            self.timestamp = timestamp.replace(tzinfo=UTC)
        else:
            self.timestamp = timestamp.astimezone(UTC)
        self.item = item


class RollingEventBuffer(Generic[T]):
    """Thread-safe bounded circular buffer holding timestamped events."""

    def __init__(self, max_capacity: int = 50_000) -> None:
        self.max_capacity = max_capacity
        self._deque: deque[TimestampedItem[T]] = deque(maxlen=max_capacity)
        self._lock = threading.RLock()

    def append(self, item: T, timestamp: datetime) -> None:
        """Appends an event with its timestamp. Thread-safe O(1)."""
        wrapped = TimestampedItem(item, timestamp)
        with self._lock:
            self._deque.append(wrapped)

    def get_window(
        self,
        start_time: datetime,
        end_time: datetime | None = None,
    ) -> list[T]:
        """Retrieves items within [start_time, end_time]."""
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        else:
            start_time = start_time.astimezone(UTC)

        if end_time is not None:
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=UTC)
            else:
                end_time = end_time.astimezone(UTC)

        with self._lock:
            result: list[T] = []
            for entry in self._deque:
                if entry.timestamp >= start_time:
                    if end_time is None or entry.timestamp <= end_time:
                        result.append(entry.item)
            return result

    def prune_older_than(self, cutoff: datetime) -> int:
        """Removes all items with timestamp strictly older than cutoff."""
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=UTC)
        else:
            cutoff = cutoff.astimezone(UTC)

        pruned = 0
        with self._lock:
            while self._deque and self._deque[0].timestamp < cutoff:
                self._deque.popleft()
                pruned += 1
        return pruned

    def count(self) -> int:
        """Returns total items currently stored."""
        with self._lock:
            return len(self._deque)

    def clear(self) -> None:
        """Flushes the buffer."""
        with self._lock:
            self._deque.clear()


class SLIEventBufferManager:
    """Manages segregated rolling buffers across all SLI categories and services."""

    def __init__(self, max_capacity_per_sli: int = 100_000) -> None:
        self.max_capacity = max_capacity_per_sli
        self._buffers: dict[SLICategory, RollingEventBuffer[ServiceLevelIndicatorMeasurement]] = {}
        self._lock = threading.RLock()

    def _get_buffer(
        self, sli_name: SLICategory
    ) -> RollingEventBuffer[ServiceLevelIndicatorMeasurement]:
        with self._lock:
            if sli_name not in self._buffers:
                self._buffers[sli_name] = RollingEventBuffer(max_capacity=self.max_capacity)
            return self._buffers[sli_name]

    def record_measurement(self, measurement: ServiceLevelIndicatorMeasurement) -> None:
        """Appends an SLI measurement into its respective category buffer."""
        buf = self._get_buffer(measurement.sli_name)
        buf.append(measurement, measurement.timestamp)

    def get_measurements(
        self,
        sli_name: SLICategory,
        start_time: datetime,
        end_time: datetime | None = None,
    ) -> list[ServiceLevelIndicatorMeasurement]:
        """Retrieves measurements for an SLI within a time window."""
        buf = self._get_buffer(sli_name)
        return buf.get_window(start_time, end_time)

    def get_counts(
        self,
        sli_name: SLICategory,
        start_time: datetime,
        end_time: datetime | None = None,
    ) -> tuple[int, int]:
        """Returns (total_events, compliant_events) in the window."""
        measurements = self.get_measurements(sli_name, start_time, end_time)
        total = len(measurements)
        compliant = sum(1 for m in measurements if m.is_compliant)
        return total, compliant

    def get_observed_values(
        self,
        sli_name: SLICategory,
        start_time: datetime,
        end_time: datetime | None = None,
    ) -> list[float]:
        """Returns raw observed values for percentile latency calculations."""
        measurements = self.get_measurements(sli_name, start_time, end_time)
        return [m.observed_value for m in measurements]

    def prune_older_than(self, cutoff: datetime) -> int:
        """Prunes historical events across all buffers."""
        with self._lock:
            total_pruned = 0
            for buf in self._buffers.values():
                total_pruned += buf.prune_older_than(cutoff)
            return total_pruned

    def total_events_count(self) -> int:
        """Returns aggregate event count across all SLIs."""
        with self._lock:
            return sum(buf.count() for buf in self._buffers.values())

    def clear(self) -> None:
        """Clears all category buffers."""
        with self._lock:
            for buf in self._buffers.values():
                buf.clear()
