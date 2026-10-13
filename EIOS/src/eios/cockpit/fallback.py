"""Deterministic Replay & Graceful Degradation Engine.

Pursuant to Constitution Principle VIII (Deterministic Fallback and Operability),
service disruptions or LLM gateway outages degrade gracefully to precomputed,
verified snapshots stamped with prominent amber [REPLAY] status badges.
Invented or hallucinated text is strictly prohibited.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceHealthState(str, Enum):
    HEALTHY_LIVE = "HEALTHY_LIVE"
    DEGRADED_REPLAY = "DEGRADED_REPLAY"
    OUTAGE_CACHED = "OUTAGE_CACHED"


class FallbackBadge(BaseModel):
    badge_label: str = "[REPLAY]"
    badge_color: str = "#b45309"  # Amber-700
    is_fallback: bool = True
    snapshot_timestamp: datetime
    message: str = (
        "Live synthesis engine is currently unavailable. Displaying precomputed verified snapshot."
    )


class FallbackEngine:
    """Manages cached view snapshots and executes automatic failover."""

    def __init__(self) -> None:
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._health_state: ServiceHealthState = ServiceHealthState.HEALTHY_LIVE
        self._failover_count: int = 0

    def register_snapshot(self, view_key: str, data: dict[str, Any]) -> None:
        """Stores a verified pre-computed snapshot for a view."""
        self._snapshots[view_key] = {
            "payload": data,
            "captured_at": datetime.now(UTC),
        }

    def get_snapshot(self, view_key: str) -> dict[str, Any]:
        """Retrieves a snapshot stamped with [REPLAY] badge metadata."""
        if view_key not in self._snapshots:
            raise KeyError(f"No cached snapshot registered for view: {view_key}")

        entry = self._snapshots[view_key]
        payload = dict(entry["payload"])
        captured_at = entry["captured_at"]

        badge = FallbackBadge(
            snapshot_timestamp=captured_at,
        )

        payload["is_cached_fallback"] = True
        payload["fallback_badge"] = badge.model_dump()
        payload["fallback_badge"]["snapshot_timestamp"] = captured_at.isoformat()
        return payload

    def execute_with_fallback(
        self,
        view_key: str,
        live_callable: Callable[..., dict[str, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Executes live_callable; falls back to verified cached snapshot on error."""
        try:
            result = live_callable(*args, **kwargs)
            self._health_state = ServiceHealthState.HEALTHY_LIVE
            # Automatically update warm snapshot on successful live execution
            self.register_snapshot(view_key, result)
            return result
        except Exception as exc:
            self._health_state = ServiceHealthState.DEGRADED_REPLAY
            self._failover_count += 1
            logger.warning(
                "Primary live provider call failed for view %s (%s). Engaging deterministic fallback.",
                view_key,
                str(exc),
            )
            return self.get_snapshot(view_key)

    @property
    def health_state(self) -> ServiceHealthState:
        return self._health_state

    @property
    def failover_count(self) -> int:
        return self._failover_count
