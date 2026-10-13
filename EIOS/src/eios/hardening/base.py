"""Base chaos injection hooks and fault interceptor interfaces."""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class FaultType(str, Enum):
    PROCESS_CRASH = "PROCESS_CRASH"
    DLQ_FLOOD = "DLQ_FLOOD"
    LLM_OUTAGE = "LLM_OUTAGE"
    DUPLICATE_NONCE = "DUPLICATE_NONCE"
    LEDGER_TAMPER = "LEDGER_TAMPER"
    NETWORK_LAG = "NETWORK_LAG"


class ChaosInjectionHook:
    """Thread-safe context manager for temporarily injecting faults into target components."""

    _active_faults: dict[str, dict[str, Any]] = {}
    _lock = threading.RLock()

    def __init__(
        self,
        fault_type: FaultType | str,
        target_subsystem: str,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        self.fault_type = fault_type.value if hasattr(fault_type, "value") else str(fault_type)
        self.target_subsystem = target_subsystem
        self.parameters = parameters or {}
        self.experiment_id = str(uuid.uuid4())
        self.injected_at: datetime | None = None

    def __enter__(self) -> ChaosInjectionHook:
        with self._lock:
            self.injected_at = datetime.now(UTC)
            self._active_faults[self.target_subsystem] = {
                "experiment_id": self.experiment_id,
                "fault_type": self.fault_type,
                "parameters": self.parameters,
                "injected_at": self.injected_at,
            }
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        with self._lock:
            self._active_faults.pop(self.target_subsystem, None)

    @classmethod
    def get_active_fault(cls, target_subsystem: str) -> dict[str, Any] | None:
        """Retrieves active fault injection config for a target subsystem."""
        with cls._lock:
            return cls._active_faults.get(target_subsystem)

    @classmethod
    def is_fault_active(
        cls, target_subsystem: str, fault_type: str | FaultType | None = None
    ) -> bool:
        """Checks if a fault is currently active on a target subsystem."""
        with cls._lock:
            active = cls._active_faults.get(target_subsystem)
            if active is None:
                return False
            if fault_type is not None:
                expected = fault_type.value if hasattr(fault_type, "value") else str(fault_type)
                if active.get("fault_type") != expected:
                    return False
            return True

    @classmethod
    def clear_all_faults(cls) -> None:
        """Clears all active fault hooks."""
        with cls._lock:
            cls._active_faults.clear()
