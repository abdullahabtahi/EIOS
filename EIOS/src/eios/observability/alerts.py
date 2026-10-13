"""Multi-Window Multi-Burn-Rate SRE Alerting Policies and Alert Router.

Implements Google SRE Handbook Chapter 5 dual-window confirmation alerting
(14.4x 1h + 5m short-window confirmation -> Page SEV-1; 6x 6h + 30m short-window -> Ticket SEV-2),
Dead-Letter Queue depth monitoring, SEV-1 cryptographic ledger mismatch alerts,
and flapping hysteresis suppression.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from eios.observability.slo_catalog import SLICategory
from eios.observability.slo_engine import SLOMonitoringEngine


class SREAlertSeverity(str, Enum):
    PAGE_CRITICAL_SEV1 = "PAGE_CRITICAL_SEV1"  # Immediate pager dispatch
    TICKET_HIGH_SEV2 = "TICKET_HIGH_SEV2"  # Urgent ticket queue
    TICKET_MEDIUM_SEV3 = "TICKET_MEDIUM_SEV3"  # Standard queue ticket
    INFO = "INFO"


class SREAlertEvent(BaseModel):
    """Notification emitted by multi-window burn rate policies and system monitors."""

    alert_id: str = Field(..., description="Unique alert UUID")
    policy_name: str = Field(..., description="Triggered alerting policy rule name")
    severity: SREAlertSeverity = Field(..., description="Alert severity level")
    sli_name: SLICategory | None = Field(None, description="Associated SLI if applicable")
    service_name: str = Field(..., description="Affected service")
    burn_rate: float = Field(default=0.0, ge=0.0, description="Observed burn rate multiplier")
    message: str = Field(..., description="Human-readable diagnostic summary")
    triggered_at: datetime = Field(..., description="Trigger timestamp in UTC")
    is_active: bool = Field(default=True, description="True if currently firing")


class SREAlertEngine:
    """Manages multi-window alerting policies, dual confirmation, and critical monitors."""

    def __init__(
        self,
        slo_engine: SLOMonitoringEngine | None = None,
        hysteresis_minutes: int = 15,
    ) -> None:
        self.slo_engine = slo_engine or SLOMonitoringEngine()
        self.hysteresis_minutes = hysteresis_minutes
        self._alerts: dict[str, SREAlertEvent] = {}
        self._last_alert_time: dict[str, datetime] = {}
        self._lock = threading.RLock()

    def _should_suppress_alert(self, key: str, timestamp: datetime) -> bool:
        """Suppresses duplicate alert if within hysteresis window."""
        with self._lock:
            last = self._last_alert_time.get(key)
            if last is not None:
                if (timestamp - last) < timedelta(minutes=self.hysteresis_minutes):
                    return True
            self._last_alert_time[key] = timestamp
            return False

    def evaluate_alerts(self, reference_time: datetime | None = None) -> list[SREAlertEvent]:
        """Evaluates Google SRE dual-window burn rate conditions across all SLOs."""
        ref_time = reference_time or datetime.now(UTC)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=UTC)

        newly_fired: list[SREAlertEvent] = []

        for sli_cat, config in self.slo_engine.catalog.items():
            target_pct = config.target_percentage

            # 1. Dual-Window Check for Page SEV-1 (14.4x burn rate)
            # Long window = 1 hour; Short window = 5 minutes
            burn_1h = self.slo_engine._compute_burn_rate(
                sli_cat, target_pct, timedelta(hours=1), ref_time
            )
            burn_5m = self.slo_engine._compute_burn_rate(
                sli_cat, target_pct, timedelta(minutes=5), ref_time
            )

            if burn_1h >= 14.4 and burn_5m >= 14.4:
                policy_key = f"PAGE_SEV1_{sli_cat.value}"
                if not self._should_suppress_alert(policy_key, ref_time):
                    alert = SREAlertEvent(
                        alert_id=str(uuid.uuid4()),
                        policy_name="Page SEV-1: Rapid Error Budget Consumption (14.4x in 1h)",
                        severity=SREAlertSeverity.PAGE_CRITICAL_SEV1,
                        sli_name=sli_cat,
                        service_name=sli_cat.value,
                        burn_rate=round(burn_1h, 2),
                        message=f"Critical burn rate on {config.display_name}: 1h burn={burn_1h:.1f}x and 5m short-window burn={burn_5m:.1f}x exceed 14.4x threshold.",
                        triggered_at=ref_time,
                        is_active=True,
                    )
                    with self._lock:
                        self._alerts[alert.alert_id] = alert
                    newly_fired.append(alert)
                    continue  # Pager takes precedence over ticket

            # 2. Dual-Window Check for Ticket SEV-2 (6.0x burn rate)
            # Long window = 6 hours; Short window = 30 minutes
            burn_6h = self.slo_engine._compute_burn_rate(
                sli_cat, target_pct, timedelta(hours=6), ref_time
            )
            burn_30m = self.slo_engine._compute_burn_rate(
                sli_cat, target_pct, timedelta(minutes=30), ref_time
            )

            if burn_6h >= 6.0 and burn_30m >= 6.0:
                policy_key = f"TICKET_SEV2_{sli_cat.value}"
                if not self._should_suppress_alert(policy_key, ref_time):
                    alert = SREAlertEvent(
                        alert_id=str(uuid.uuid4()),
                        policy_name="Ticket SEV-2: Elevated Error Budget Consumption (6.0x in 6h)",
                        severity=SREAlertSeverity.TICKET_HIGH_SEV2,
                        sli_name=sli_cat,
                        service_name=sli_cat.value,
                        burn_rate=round(burn_6h, 2),
                        message=f"Elevated burn rate on {config.display_name}: 6h burn={burn_6h:.1f}x and 30m short-window burn={burn_30m:.1f}x exceed 6.0x threshold.",
                        triggered_at=ref_time,
                        is_active=True,
                    )
                    with self._lock:
                        self._alerts[alert.alert_id] = alert
                    newly_fired.append(alert)
                    continue

            # 3. Dual-Window Check for Ticket SEV-3 (1.0x burn rate)
            # Long window = 24 hours; Short window = 2 hours
            burn_24h = self.slo_engine._compute_burn_rate(
                sli_cat, target_pct, timedelta(hours=24), ref_time
            )
            burn_2h = self.slo_engine._compute_burn_rate(
                sli_cat, target_pct, timedelta(hours=2), ref_time
            )

            if burn_24h >= 1.0 and burn_2h >= 1.0:
                policy_key = f"TICKET_SEV3_{sli_cat.value}"
                if not self._should_suppress_alert(policy_key, ref_time):
                    alert = SREAlertEvent(
                        alert_id=str(uuid.uuid4()),
                        policy_name="Ticket SEV-3: Steady Error Budget Consumption (1.0x in 24h)",
                        severity=SREAlertSeverity.TICKET_MEDIUM_SEV3,
                        sli_name=sli_cat,
                        service_name=sli_cat.value,
                        burn_rate=round(burn_24h, 2),
                        message=f"Steady budget consumption on {config.display_name}: 24h burn={burn_24h:.1f}x exceeds 1.0x baseline.",
                        triggered_at=ref_time,
                        is_active=True,
                    )
                    with self._lock:
                        self._alerts[alert.alert_id] = alert
                    newly_fired.append(alert)

        return newly_fired

    def emit_ledger_integrity_alert(
        self,
        service_name: str,
        expected_seq: int,
        actual_seq: int,
        previous_hash: str,
        current_hash: str,
        timestamp: datetime | None = None,
    ) -> SREAlertEvent:
        """Immediately emits a Page SEV-1 on cryptographic ledger chain sequence mismatch."""
        ts = timestamp or datetime.now(UTC)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        alert = SREAlertEvent(
            alert_id=str(uuid.uuid4()),
            policy_name="Cryptographic Ledger Integrity Breach",
            severity=SREAlertSeverity.PAGE_CRITICAL_SEV1,
            sli_name=SLICategory.LEDGER_CHAIN_INTEGRITY,
            service_name=service_name,
            burn_rate=14.4,
            message=f"Ledger cryptographic mismatch in {service_name}: expected sequence {expected_seq}, observed {actual_seq}. Hash linkage verification failed (prev: {previous_hash[:8]}, cur: {current_hash[:8]}).",
            triggered_at=ts,
            is_active=True,
        )
        with self._lock:
            self._alerts[alert.alert_id] = alert
        return alert

    def emit_dlq_backlog_alert(
        self,
        service_name: str,
        dlq_depth: int,
        threshold: int = 100,
        timestamp: datetime | None = None,
    ) -> SREAlertEvent:
        """Emits Ticket SEV-2 alert when Dead-Letter Queue exceeds capacity threshold."""
        ts = timestamp or datetime.now(UTC)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        alert = SREAlertEvent(
            alert_id=str(uuid.uuid4()),
            policy_name="DLQ Backlog Threshold Exceeded",
            severity=SREAlertSeverity.TICKET_HIGH_SEV2,
            sli_name=SLICategory.CONTRACT_ENFORCEMENT,
            service_name=service_name,
            burn_rate=6.0,
            message=f"DLQ backlog breach in {service_name}: depth is {dlq_depth} messages (threshold: {threshold}).",
            triggered_at=ts,
            is_active=True,
        )
        with self._lock:
            self._alerts[alert.alert_id] = alert
        return alert

    def get_active_alerts(self) -> list[SREAlertEvent]:
        """Returns all currently firing alert events."""
        with self._lock:
            return [a for a in self._alerts.values() if a.is_active]

    def resolve_alert(self, alert_id: str) -> None:
        """Marks an alert as resolved."""
        with self._lock:
            if alert_id in self._alerts:
                self._alerts[alert_id].is_active = False


def alert_to_contract_dict(alert: SREAlertEvent) -> dict[str, Any]:
    """Converts SREAlertEvent to dictionary matching sre-alert-event.schema.json."""
    data: dict[str, Any] = {
        "alert_id": alert.alert_id,
        "policy_name": alert.policy_name,
        "severity": alert.severity.value,
        "service_name": alert.service_name,
        "burn_rate": alert.burn_rate,
        "message": alert.message,
        "triggered_at": alert.triggered_at.isoformat(),
        "is_active": alert.is_active,
    }
    if alert.sli_name is not None:
        data["sli_name"] = alert.sli_name.value
    return data
