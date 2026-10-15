"""Hedged model calls: a second identical call when the first is slow, whichever answers first wins.

The shared model endpoint is erratic: the same small prompt answers in 2 s or in 30 s or more, and a stalled call holds a
whole turn past its deadline. A call that has not answered after `hedge_after_s` is therefore sent once more and the first
answer wins; the other is cancelled. A model call has no side effects (tools are run by the platform from the answer), so
sending it twice is safe. The cost is one extra call, only on the calls that were already slow. At most one hedge is
started per call, so slowness cannot multiply requests. Streaming is passed through untouched.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from pydantic import ConfigDict

logger = logging.getLogger(__name__)


def _clone(request: LlmRequest) -> LlmRequest:
    """A request one call may change without affecting the other. The tool objects it refers to hold locks and are shared,
    never copied; the message list and the generation settings, which a call may adjust, are."""
    copy = request.model_copy()
    copy.contents = list(request.contents)
    copy.config = request.config.model_copy(deep=True)
    return copy


async def _collect(inner: BaseLlm, request: LlmRequest) -> list[LlmResponse]:
    return [response async for response in inner.generate_content_async(request, stream=False)]


class HedgedLlm(BaseLlm):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    inner: BaseLlm
    hedge_after_s: float

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        if stream or self.hedge_after_s <= 0:
            async for response in self.inner.generate_content_async(llm_request, stream=stream):
                yield response
            return
        first = asyncio.create_task(_collect(self.inner, _clone(llm_request)))
        tasks: set[asyncio.Task[list[LlmResponse]]] = {first}
        try:
            await asyncio.wait({first}, timeout=self.hedge_after_s)
            if not first.done():
                logger.info("model call slow after %.1fs; sending a hedge", self.hedge_after_s)
                tasks.add(asyncio.create_task(_collect(self.inner, _clone(llm_request))))
            result = await self._first_success(tasks)
            if first.done() is False:
                logger.info("the hedge answered first")
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
        for response in result:
            yield response

    @staticmethod
    async def _first_success(tasks: set[asyncio.Task[list[LlmResponse]]]) -> list[LlmResponse]:
        """The first call to answer. A call that failed is passed over while another is still running."""
        pending = set(tasks)
        error: BaseException | None = None
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if task.exception() is None:
                    return task.result()
                error = error or task.exception()
        # every call failed: report the first failure, as an unhedged call would
        raise error if error is not None else RuntimeError("no model call was made")


def hedged(inner: BaseLlm, hedge_after_s: float) -> BaseLlm:
    """`inner`, hedged after `hedge_after_s` seconds; the model itself when hedging is off."""
    if hedge_after_s <= 0:
        return inner
    return HedgedLlm(model=inner.model, inner=inner, hedge_after_s=hedge_after_s)
