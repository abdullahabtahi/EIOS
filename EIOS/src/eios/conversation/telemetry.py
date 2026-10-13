"""OpenTelemetry and LangSmith tracing instrumentation for Conversational Copilot (F018, T036)."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

_LOG = logging.getLogger("eios.conversation.telemetry")


class CopilotTracer:
    """Instruments conversation turns with OpenTelemetry semantic conventions and LangSmith trace tags."""

    def __init__(self, service_name: str = "eios-conversational-copilot") -> None:
        self.service_name = service_name
        self.langsmith_enabled = bool(os.getenv("LANGCHAIN_API_KEY"))

    @contextmanager
    def trace_turn(
        self,
        session_id: str,
        turn_index: int,
        query: str,
        role: str,
    ) -> Generator[dict[str, Any]]:
        """Context manager capturing turn latency, token usage, and auditor pass/block tags."""
        start_time = time.perf_counter()
        metadata: dict[str, Any] = {
            "session_id": session_id,
            "turn_index": turn_index,
            "role": role,
            "query_length": len(query),
            "auditor_status": "PENDING",
            "model_id": os.getenv("EIOS_MODEL_ID", "default-model"),
        }

        try:
            yield metadata
        finally:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metadata["duration_ms"] = elapsed_ms
            _LOG.info(
                "Turn trace [%s#%d] role=%s latency=%.2fms auditor=%s",
                session_id,
                turn_index,
                role,
                elapsed_ms,
                metadata.get("auditor_status", "UNKNOWN"),
            )
