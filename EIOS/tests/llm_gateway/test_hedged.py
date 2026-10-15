"""Hedged model calls: a slow call gets one second chance, the first answer wins, a failure is passed over."""

import asyncio
import time
from collections.abc import AsyncGenerator

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from pydantic import ConfigDict

from eios.llm_gateway.providers.adk_types import Content, Part
from eios.llm_gateway.providers.hedged import HedgedLlm, hedged


class FakeLlm(BaseLlm):
    """Answers call n after delays[n] seconds, or fails when failures[n] is set."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    model: str = "fake"
    delays: list[float] = []
    failures: list[bool] = []
    calls: int = 0
    cancelled: int = 0

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        n = self.calls
        self.calls += 1
        try:
            await asyncio.sleep(self.delays[n] if n < len(self.delays) else 0)
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        if n < len(self.failures) and self.failures[n]:
            raise RuntimeError(f"call {n} failed")
        yield LlmResponse(content=Content(role="model", parts=[Part.from_text(text=f"answer {n}")]))


async def run(llm: BaseLlm) -> tuple[str, float]:
    started = time.perf_counter()
    texts = [
        r.content.parts[0].text async for r in llm.generate_content_async(LlmRequest(model="fake"))
    ]
    return texts[0], time.perf_counter() - started


def test_a_fast_call_is_never_hedged() -> None:
    inner = FakeLlm(delays=[0.0])
    text, _ = asyncio.run(run(HedgedLlm(model="fake", inner=inner, hedge_after_s=0.3)))
    assert text == "answer 0" and inner.calls == 1


def test_a_stalled_call_is_answered_by_the_hedge_and_the_stalled_one_is_cancelled() -> None:
    inner = FakeLlm(delays=[5.0, 0.0])
    text, took = asyncio.run(run(HedgedLlm(model="fake", inner=inner, hedge_after_s=0.2)))
    assert text == "answer 1" and inner.calls == 2
    assert took < 1.0  # not the 5 s the stalled call would have taken
    assert inner.cancelled == 1


def test_at_most_one_hedge_is_sent() -> None:
    inner = FakeLlm(delays=[1.0, 1.0, 1.0])
    asyncio.run(run(HedgedLlm(model="fake", inner=inner, hedge_after_s=0.1)))
    assert inner.calls == 2


def test_a_failed_first_call_is_passed_over_when_the_hedge_can_answer() -> None:
    inner = FakeLlm(delays=[0.3, 0.0], failures=[True, False])
    text, _ = asyncio.run(run(HedgedLlm(model="fake", inner=inner, hedge_after_s=0.1)))
    assert text == "answer 1"


def test_when_every_call_fails_the_first_error_is_raised() -> None:
    inner = FakeLlm(delays=[0.3, 0.3], failures=[True, True])
    with pytest.raises(RuntimeError, match="call 0 failed"):
        asyncio.run(run(HedgedLlm(model="fake", inner=inner, hedge_after_s=0.1)))


def test_hedging_off_returns_the_model_itself() -> None:
    inner = FakeLlm()
    assert hedged(inner, 0) is inner
    assert isinstance(hedged(inner, 5.0), HedgedLlm)


def test_a_real_request_with_tools_that_hold_locks_can_be_hedged() -> None:
    import threading
    from typing import Any

    from google.adk.tools.base_tool import BaseTool

    class LockedTool(BaseTool):
        def __init__(self) -> None:
            super().__init__(name="locked", description="holds a lock")
            self.lock = threading.Lock()

        async def run_async(self, *, args: dict[str, Any], tool_context: Any) -> dict[str, Any]:
            return {}

    inner = FakeLlm(delays=[2.0, 0.0])
    request = LlmRequest(model="fake", tools_dict={"locked": LockedTool()})
    llm = HedgedLlm(model="fake", inner=inner, hedge_after_s=0.1)

    async def go() -> str:
        return [r.content.parts[0].text async for r in llm.generate_content_async(request)][0]

    assert asyncio.run(go()) == "answer 1" and inner.calls == 2
