"""Platform operational metrics and planted outage shock generator (FR-045)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from eios.foundry.contracts import ContractValidator, OperationalMetricRecord
from eios.foundry.rng import RNGManager

SERVICES = ["order-router", "kyc-verifier", "payment-gateway", "websocket-feed"]


class OperationalDataGenerator:
    """Generates hourly operational metrics with realistic noise and exactly 1 planted outage shock."""

    def __init__(self, rng: RNGManager) -> None:
        self.rng = rng
        self._gen = rng.get_generator("operational_metrics")
        self._validator = ContractValidator(OperationalMetricRecord)

    def generate_metrics(self, hours: int = 48) -> list[dict[str, Any]]:
        """Generates validated hourly operational telemetry containing 1 incident shock."""
        records: list[dict[str, Any]] = []
        base_dt = datetime(2025, 3, 10, 0, 0, 0, tzinfo=UTC)

        # Planted shock between hour 20 and 24
        shock_start_hour = 20
        shock_end_hour = 24

        for h in range(hours):
            current_dt = base_dt + timedelta(hours=h)
            is_shock = shock_start_hour <= h < shock_end_hour

            for _s_idx, service in enumerate(SERVICES):
                if is_shock and service == "payment-gateway":
                    latency = float(self._gen.uniform(1200.0, 1800.0))
                    disputes = int(self._gen.integers(15, 30))
                    err_rate = float(self._gen.uniform(0.12, 0.25))
                    active_inc = True
                else:
                    latency = float(self._gen.uniform(45.0, 120.0))
                    disputes = int(self._gen.integers(0, 3))
                    err_rate = float(self._gen.uniform(0.0001, 0.005))
                    active_inc = False

                records.append(
                    {
                        "timestamp": current_dt.isoformat(),
                        "service_name": service,
                        "p95_latency_ms": latency,
                        "dispute_ticket_count": disputes,
                        "error_rate": err_rate,
                        "is_incident_active": active_inc,
                    }
                )

        self._validator.validate_batch(records)
        return records
