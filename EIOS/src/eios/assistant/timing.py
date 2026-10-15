"""Where a turn's time went: each model call and each tool call is timed where it happens.

A `TurnTimer` is put in a context variable for the duration of a turn. `timed(model)` wraps a model so every call (a
hedge included) adds its duration to the current timer, and `TimingPlugin` does the same for tool calls. Whatever is
left of the turn's wall time (session load, screening, the assembler, ADK itself) is reported as `other`. Timing is
outside the model and the plugins that screen it, so screening time is never blamed on the model. No timer, no cost.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from pydantic import ConfigDict


@dataclass
class TurnTimer:
    model_calls_ms: list[float] = field(default_factory=list)
    tool_calls_ms: list[float] = field(default_factory=list)
    _tool_starts: dict[str, float] = field(default_factory=dict, repr=False)

    def breakdown(self, wall_ms: float) -> dict[str, Any]:
        model, tools = sum(self.model_calls_ms), sum(self.tool_calls_ms)
        return {
            "model": round(model, 1),
            "tools": round(tools, 1),
            "other": round(max(0.0, wall_ms - model - tools), 1),
            "model_calls": [round(ms, 1) for ms in self.model_calls_ms],
        }


_current: ContextVar[TurnTimer | None] = ContextVar("turn_timer", default=None)


def start_turn_timer() -> TurnTimer:
    timer = TurnTimer()
    _current.set(timer)
    return timer


class TimedLlm(BaseLlm):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    inner: BaseLlm

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        started = time.perf_counter()
        try:
            async for response in self.inner.generate_content_async(llm_request, stream=stream):
                yield response
        finally:
            timer = _current.get()
            if timer is not None:
                timer.model_calls_ms.append((time.perf_counter() - started) * 1000)


def timed(inner: BaseLlm) -> BaseLlm:
    return TimedLlm(model=inner.model, inner=inner)


class TimingPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(name="timing")

    async def before_tool_callback(
        self, *, tool: Any, tool_args: dict[str, Any], tool_context: Any
    ) -> None:
        timer = _current.get()
        if timer is not None:
            timer._tool_starts[tool_context.function_call_id or tool.name] = time.perf_counter()

    async def after_tool_callback(
        self, *, tool: Any, tool_args: dict[str, Any], tool_context: Any, result: dict[str, Any]
    ) -> None:
        self._close(tool, tool_context)

    async def on_tool_error_callback(
        self, *, tool: Any, tool_args: dict[str, Any], tool_context: Any, error: Exception
    ) -> None:
        self._close(tool, tool_context)

    @staticmethod
    def _close(tool: Any, tool_context: Any) -> None:
        timer = _current.get()
        started = (
            timer._tool_starts.pop(tool_context.function_call_id or tool.name, None)
            if timer
            else None
        )
        if timer is not None and started is not None:
            timer.tool_calls_ms.append((time.perf_counter() - started) * 1000)
