"""Circuit breaker monitoring rolling contract breach rates and managing product health status."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import threading

from eios.contracts.base import DataProductEnum


class ProductHealthStatus(str, Enum):
    """Health status for a Layer 1 Data Product."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


@dataclass
class ProductBreachMetrics:
    """Metrics snapshot for product contract adherence."""
    total_events: int
    breach_count: int
    breach_rate: float
    status: ProductHealthStatus


class IngestionCircuitBreaker:
    """Calculates rolling breach rates and triggers DEGRADED state when exceeding threshold."""

    def __init__(
        self,
        breach_rate_threshold: float = 0.0005,  # 0.05%
        window_seconds: int = 3600,  # 1 hour
    ) -> None:
        self.breach_rate_threshold = breach_rate_threshold
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        
        # Deques of (timestamp, is_breach: bool) per product
        self._events: dict[DataProductEnum, deque[tuple[float, bool]]] = {
            product: deque() for product in DataProductEnum
        }

    def _prune(self, product: DataProductEnum, now_ts: float) -> None:
        """Remove events older than the rolling window."""
        cutoff = now_ts - self.window_seconds
        q = self._events[product]
        while q and q[0][0] < cutoff:
            q.popleft()

    def record_success(self, product: DataProductEnum) -> None:
        """Record a successfully validated payload."""
        now_ts = datetime.now(timezone.utc).timestamp()
        with self._lock:
            if product not in self._events:
                self._events[product] = deque()
            self._events[product].append((now_ts, False))
            self._prune(product, now_ts)

    def record_breach(self, product: DataProductEnum) -> None:
        """Record a contract breach."""
        now_ts = datetime.now(timezone.utc).timestamp()
        with self._lock:
            if product not in self._events:
                self._events[product] = deque()
            self._events[product].append((now_ts, True))
            self._prune(product, now_ts)

    def get_metrics(self, product: DataProductEnum) -> ProductBreachMetrics:
        """Compute rolling breach metrics for a given product."""
        now_ts = datetime.now(timezone.utc).timestamp()
        with self._lock:
            if product not in self._events:
                return ProductBreachMetrics(0, 0, 0.0, ProductHealthStatus.HEALTHY)
            self._prune(product, now_ts)
            q = self._events[product]
            total = len(q)
            if total == 0:
                return ProductBreachMetrics(0, 0, 0.0, ProductHealthStatus.HEALTHY)
            breaches = sum(1 for _, is_b in q if is_b)
            rate = breaches / total
            status = ProductHealthStatus.DEGRADED if rate > self.breach_rate_threshold else ProductHealthStatus.HEALTHY
            return ProductBreachMetrics(total, breaches, rate, status)

    def get_status(self, product: DataProductEnum) -> ProductHealthStatus:
        """Get current health status of a product."""
        return self.get_metrics(product).status
