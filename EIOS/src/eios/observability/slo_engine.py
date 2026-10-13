"""Continuous 10-SLO Evaluation Engine & 28-Day Error Budget Tracker.

Evaluates Google SRE multi-window burn rates (1h, 6h, 24h), rolling 28-day error budgets,
automated FEATURE_FREEZE release gates for Tier 1 Critical services, and Four-Eyes
break-glass authorization.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from eios.observability.buffer import (
    ServiceLevelIndicatorMeasurement,
    SLIEventBufferManager,
)
from eios.observability.slo_catalog import (
    DEFAULT_SLO_CATALOG,
    ServiceLevelObjectiveConfig,
    SLICategory,
    SLOTier,
)


class ErrorBudgetHealth(str, Enum):
    """Operational health state determined by remaining error budget balance."""

    HEALTHY = "HEALTHY"  # Budget remaining >= 20.0%
    WARNING = "WARNING"  # 0.0% < Budget remaining < 20.0%
    FEATURE_FREEZE = "FEATURE_FREEZE"  # Budget remaining <= 0.0%


class ErrorBudgetStatus(BaseModel):
    """Rolling error budget balance, compliance metrics, and release freeze state."""

    sli_name: SLICategory = Field(..., description="SLI evaluated")
    window_days: int = Field(default=28, ge=1, description="Evaluation window duration in days")
    total_events: int = Field(..., ge=0, description="Total observed events in window")
    compliant_events: int = Field(..., ge=0, description="Total compliant events in window")
    failed_events: int = Field(..., ge=0, description="Total non-compliant events in window")
    compliance_percentage: float = Field(
        ..., ge=0.0, le=100.0, description="Observed compliance percentage"
    )
    target_percentage: float = Field(
        ..., ge=0.0, le=100.0, description="Target SLO percentage (e.g. 99.5)"
    )
    budget_remaining_pct: float = Field(
        ..., description="Remaining error budget percentage (may be negative if depleted)"
    )
    burn_rate_1h: float = Field(
        default=0.0, ge=0.0, description="Observed 1-hour burn rate multiplier"
    )
    burn_rate_6h: float = Field(
        default=0.0, ge=0.0, description="Observed 6-hour burn rate multiplier"
    )
    burn_rate_24h: float = Field(
        default=0.0, ge=0.0, description="Observed 24-hour burn rate multiplier"
    )
    status: ErrorBudgetHealth = Field(..., description="Operational status based on budget balance")
    is_frozen: bool = Field(
        ..., description="True if release freeze is active due to Tier 1 budget exhaustion"
    )


class BreakGlassOverrideRequest(BaseModel):
    """Four-Eyes break-glass authorization request."""

    approver_1: str = Field(..., description="Primary authenticated human approver identifier")
    approver_2: str = Field(
        ..., description="Secondary distinct authenticated human approver identifier"
    )
    justification: str = Field(
        ..., min_length=10, description="Operational justification for hotfix"
    )
    expires_at: datetime = Field(..., description="Expiration timestamp for the override")


class BreakGlassOverride(BaseModel):
    """Authorized break-glass override record."""

    override_id: str = Field(..., description="Unique override identifier")
    approver_1: str = Field(...)
    approver_2: str = Field(...)
    justification: str = Field(...)
    created_at: datetime = Field(...)
    expires_at: datetime = Field(...)
    is_active: bool = Field(default=True)


class ReleaseGateVerdict(BaseModel):
    """Automated release freeze gate verdict."""

    is_allowed: bool = Field(..., description="True if deployment/release is permitted")
    status: ErrorBudgetHealth = Field(..., description="Overall platform reliability health")
    reason: str = Field(..., description="Explanation of gate verdict")
    active_frozen_slis: list[SLICategory] = Field(
        default_factory=list, description="Frozen Tier 1 SLIs"
    )
    override_id: str | None = Field(None, description="Active break-glass override ID if used")


class SLOMonitoringEngine:
    """Continuous evaluation engine for production SLOs, error budgets, and release gates."""

    def __init__(
        self,
        buffer_manager: SLIEventBufferManager | None = None,
        slo_catalog: dict[SLICategory, ServiceLevelObjectiveConfig] | None = None,
    ) -> None:
        self.buffer_manager = buffer_manager or SLIEventBufferManager()
        self.catalog = slo_catalog or DEFAULT_SLO_CATALOG
        self._overrides: dict[str, BreakGlassOverride] = {}
        self._lock = threading.RLock()

    def record_event(
        self,
        sli_name: SLICategory,
        observed_value: float,
        target_threshold: float,
        is_compliant: bool,
        correlation_id: str,
        service_name: str | None = None,
        timestamp: datetime | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> ServiceLevelIndicatorMeasurement:
        """Records an SLI observation into the rolling ring buffer."""
        measurement = ServiceLevelIndicatorMeasurement(
            measurement_id=str(uuid.uuid4()),
            timestamp=timestamp or datetime.now(UTC),
            sli_name=sli_name,
            observed_value=observed_value,
            target_threshold=target_threshold,
            is_compliant=is_compliant,
            correlation_id=correlation_id,
            service_name=service_name,
            attributes=attributes or {},
        )
        self.buffer_manager.record_measurement(measurement)
        return measurement

    def _compute_burn_rate(
        self,
        sli_name: SLICategory,
        target_percentage_ratio: float,
        window_duration: timedelta,
        reference_time: datetime,
    ) -> float:
        """Calculates burn rate multiplier over window_duration according to Google SRE math."""
        start_time = reference_time - window_duration
        total, compliant = self.buffer_manager.get_counts(sli_name, start_time, reference_time)
        if total == 0:
            return 0.0

        failed = total - compliant
        actual_error_rate = failed / total
        allowed_error_rate = 1.0 - target_percentage_ratio

        if allowed_error_rate <= 0.0:
            return 14.4 if failed > 0 else 0.0

        return actual_error_rate / allowed_error_rate

    def evaluate_slo(
        self,
        sli_name: SLICategory,
        reference_time: datetime | None = None,
    ) -> ErrorBudgetStatus:
        """Evaluates 28-day error budget and multi-window burn rates for an SLI."""
        ref_time = reference_time or datetime.now(UTC)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=UTC)

        config = self.catalog[sli_name]
        window_start = ref_time - timedelta(days=config.window_days)

        total, compliant = self.buffer_manager.get_counts(sli_name, window_start, ref_time)
        failed = total - compliant

        # Compliance percentage
        compliance_pct = (compliant / total * 100.0) if total > 0 else 100.0
        target_pct = config.target_percentage * 100.0

        # Allowed error rate and error budget consumption
        allowed_error_rate = 1.0 - config.target_percentage
        if allowed_error_rate <= 0.0:
            # 100% target (e.g. Ledger chain integrity or Principle I Hallucination gate)
            budget_remaining_pct = 100.0 if failed == 0 else -100.0
        elif total == 0:
            budget_remaining_pct = 100.0
        else:
            actual_error_rate = failed / total
            budget_spent_ratio = actual_error_rate / allowed_error_rate
            budget_remaining_pct = (1.0 - budget_spent_ratio) * 100.0

        # Multi-window burn rates
        burn_1h = self._compute_burn_rate(
            sli_name, config.target_percentage, timedelta(hours=1), ref_time
        )
        burn_6h = self._compute_burn_rate(
            sli_name, config.target_percentage, timedelta(hours=6), ref_time
        )
        burn_24h = self._compute_burn_rate(
            sli_name, config.target_percentage, timedelta(hours=24), ref_time
        )

        # Health state determination
        if budget_remaining_pct <= 0.0:
            status = ErrorBudgetHealth.FEATURE_FREEZE
        elif budget_remaining_pct < 20.0:
            status = ErrorBudgetHealth.WARNING
        else:
            status = ErrorBudgetHealth.HEALTHY

        # Release freeze applies only to Tier 1 Critical services when budget exhausted
        is_frozen = (status == ErrorBudgetHealth.FEATURE_FREEZE) and (
            config.tier == SLOTier.TIER_1_CRITICAL
        )

        return ErrorBudgetStatus(
            sli_name=sli_name,
            window_days=config.window_days,
            total_events=total,
            compliant_events=compliant,
            failed_events=failed,
            compliance_percentage=round(compliance_pct, 4),
            target_percentage=round(target_pct, 4),
            budget_remaining_pct=round(budget_remaining_pct, 4),
            burn_rate_1h=round(burn_1h, 4),
            burn_rate_6h=round(burn_6h, 4),
            burn_rate_24h=round(burn_24h, 4),
            status=status,
            is_frozen=is_frozen,
        )

    def evaluate_all_slos(self, reference_time: datetime | None = None) -> list[ErrorBudgetStatus]:
        """Evaluates all registered production SLOs."""
        return [self.evaluate_slo(sli, reference_time) for sli in self.catalog.keys()]

    def authorize_break_glass(self, request: BreakGlassOverrideRequest) -> BreakGlassOverride:
        """Authorizes a Four-Eyes break-glass override for emergency hotfix releases."""
        now = datetime.now(UTC)
        req_exp = (
            request.expires_at
            if request.expires_at.tzinfo
            else request.expires_at.replace(tzinfo=UTC)
        )

        if request.approver_1 == request.approver_2:
            raise ValueError(
                "Two distinct approvers required for Four-Eyes break-glass authorization (Principle II)."
            )

        if req_exp <= now:
            raise ValueError("Override expiration must be in the future.")

        override = BreakGlassOverride(
            override_id=str(uuid.uuid4()),
            approver_1=request.approver_1,
            approver_2=request.approver_2,
            justification=request.justification,
            created_at=now,
            expires_at=req_exp,
            is_active=True,
        )

        with self._lock:
            self._overrides[override.override_id] = override
        return override

    def evaluate_release_gate(
        self,
        service_name: str,
        override_id: str | None = None,
        reference_time: datetime | None = None,
    ) -> ReleaseGateVerdict:
        """Checks if a deployment/release is permitted given current error budget state."""
        ref_time = reference_time or datetime.now(UTC)
        all_statuses = self.evaluate_all_slos(ref_time)
        frozen_slis = [s.sli_name for s in all_statuses if s.is_frozen]

        if not frozen_slis:
            return ReleaseGateVerdict(
                is_allowed=True,
                status=ErrorBudgetHealth.HEALTHY,
                reason="All Tier 1 error budgets healthy. Release permitted.",
            )

        # If frozen, check for active Four-Eyes break-glass override
        if override_id:
            with self._lock:
                override = self._overrides.get(override_id)
                if override and override.is_active and override.expires_at > ref_time:
                    return ReleaseGateVerdict(
                        is_allowed=True,
                        status=ErrorBudgetHealth.FEATURE_FREEZE,
                        reason=f"Four-Eyes break-glass override authorized by {override.approver_1} and {override.approver_2}: {override.justification}",
                        active_frozen_slis=frozen_slis,
                        override_id=override_id,
                    )

        return ReleaseGateVerdict(
            is_allowed=False,
            status=ErrorBudgetHealth.FEATURE_FREEZE,
            reason=f"FEATURE_FREEZE active due to exhausted Tier 1 error budget on: {[s.value for s in frozen_slis]}",
            active_frozen_slis=frozen_slis,
        )


def error_budget_to_contract_dict(status: ErrorBudgetStatus) -> dict[str, Any]:
    """Converts ErrorBudgetStatus to dictionary matching error-budget-status.schema.json."""
    return {
        "sli_name": status.sli_name.value,
        "window_days": status.window_days,
        "total_events": status.total_events,
        "compliant_events": status.compliant_events,
        "failed_events": status.failed_events,
        "compliance_percentage": status.compliance_percentage,
        "target_percentage": status.target_percentage,
        "budget_remaining_pct": status.budget_remaining_pct,
        "burn_rate_1h": status.burn_rate_1h,
        "burn_rate_6h": status.burn_rate_6h,
        "burn_rate_24h": status.burn_rate_24h,
        "status": status.status.value,
        "is_frozen": status.is_frozen,
    }
