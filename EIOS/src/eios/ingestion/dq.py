"""Real-time Data Quality & Freshness SLA Monitoring Registry (US6)."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
from typing import Any

from eios.contracts.base import DataProductEnum
from eios.ingestion.circuit_breaker import ProductHealthStatus

FRESHNESS_SLAS: dict[DataProductEnum, float] = {
    DataProductEnum.CLIENT_360: 300.0,
    DataProductEnum.CLIENT_FUNNEL: 900.0,
    DataProductEnum.TRANSACTIONS_AML: 30.0,
    DataProductEnum.TRADING_ACTIVITY: 30.0,
    DataProductEnum.DEVICE_NETWORK_GRAPH: 60.0,
    DataProductEnum.PARTNER_360: 900.0,
    DataProductEnum.PARTNER_REFERRAL_TREE: 900.0,
    DataProductEnum.COMMISSION_LEDGER: 900.0,
    DataProductEnum.PARTNER_ENGAGEMENT_SIGNALS: 3600.0,
    DataProductEnum.PARTNER_COMMS: 900.0,
    DataProductEnum.FINANCIAL_PNL: 3600.0,
    DataProductEnum.COMPETITOR_BENCHMARKS: 86400.0,
    DataProductEnum.PLATFORM_OPERATIONS: 300.0,
    DataProductEnum.COMPLIANCE_CASES: 60.0,
}


@dataclass
class ProductDQStatus:
    """Operational DQ and Freshness SLA metrics for a single data product."""
    product_name: str
    freshness_lag_seconds: float
    freshness_sla_seconds: float
    freshness_sla_met: bool
    total_events: int
    breach_count_1h: int
    health_status: ProductHealthStatus
    null_rates: dict[str, float] = field(default_factory=dict)


class DQMonitor:
    """Thread-safe Data Quality & SLA monitoring engine."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._latest_timestamps: dict[DataProductEnum, datetime] = {}
        self._total_events: dict[DataProductEnum, int] = defaultdict(int)
        self._field_counts: dict[DataProductEnum, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._null_counts: dict[DataProductEnum, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record_event(
        self,
        product: DataProductEnum,
        event_timestamp: datetime,
        payload: dict[str, Any],
    ) -> None:
        """Record an incoming event's timestamp and field nullability."""
        with self._lock:
            # Update latest timestamp if newer
            curr_latest = self._latest_timestamps.get(product)
            if curr_latest is None or event_timestamp > curr_latest:
                self._latest_timestamps[product] = event_timestamp

            self._total_events[product] += 1

            for k, v in payload.items():
                self._field_counts[product][k] += 1
                if v is None:
                    self._null_counts[product][k] += 1

    def get_null_rates(self, product: DataProductEnum) -> dict[str, float]:
        """Compute current null rates for fields in a product."""
        with self._lock:
            rates = {}
            for field_name, total in self._field_counts[product].items():
                if total > 0:
                    nulls = self._null_counts[product][field_name]
                    rates[field_name] = round(nulls / total, 4)
            return rates

    def get_product_status(
        self,
        product: DataProductEnum,
        breach_count_1h: int = 0,
        health_status: ProductHealthStatus = ProductHealthStatus.HEALTHY,
    ) -> ProductDQStatus:
        """Calculate real-time SLA metrics for a product."""
        now = datetime.now(timezone.utc)
        sla_seconds = FRESHNESS_SLAS.get(product, 300.0)

        with self._lock:
            latest_ts = self._latest_timestamps.get(product)
            total = self._total_events[product]
            null_rates = self.get_null_rates(product)

        if latest_ts is not None:
            # Ensure timezone awareness
            if latest_ts.tzinfo is None:
                latest_ts = latest_ts.replace(tzinfo=timezone.utc)
            lag_sec = max(0.0, (now - latest_ts).total_seconds())
        else:
            lag_sec = 0.0

        sla_met = lag_sec <= sla_seconds

        return ProductDQStatus(
            product_name=product.value,
            freshness_lag_seconds=round(lag_sec, 2),
            freshness_sla_seconds=sla_seconds,
            freshness_sla_met=sla_met,
            total_events=total,
            breach_count_1h=breach_count_1h,
            health_status=health_status,
            null_rates=null_rates,
        )

    def get_all_statuses(self, circuit_breaker: Any = None) -> dict[str, Any]:
        """Generate structured status snapshot across all 14 data products."""
        statuses = {}
        for product in DataProductEnum:
            breach_count = 0
            status = ProductHealthStatus.HEALTHY
            if circuit_breaker:
                metrics = circuit_breaker.get_metrics(product)
                breach_count = metrics.breach_count
                status = metrics.status

            dq_status = self.get_product_status(
                product,
                breach_count_1h=breach_count,
                health_status=status,
            )
            statuses[product.value] = {
                "freshness_lag_seconds": dq_status.freshness_lag_seconds,
                "freshness_sla_seconds": dq_status.freshness_sla_seconds,
                "freshness_sla_met": dq_status.freshness_sla_met,
                "total_events": dq_status.total_events,
                "breach_count_1h": dq_status.breach_count_1h,
                "health_status": dq_status.health_status.value,
                "null_rates": dq_status.null_rates,
            }

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "DEGRADED" if any(s["health_status"] == "DEGRADED" for s in statuses.values()) else "HEALTHY",
            "products": statuses,
        }
