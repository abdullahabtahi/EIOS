"""A deterministic stand-in for the language model, so the real ADK runner, tools and assembler can be exercised offline.

Each step is either a tool call or a draft. The model is stateless between turns except for the step cursor, which
is how the tests script an attempt that fails assembly and a second that succeeds.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable, Sequence
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from pydantic import ConfigDict, Field

from eios.llm_gateway.providers.adk_types import Content, Part

Step = tuple[str, str, dict[str, Any]]  # ("call", tool, arguments) or ("text", draft, {})
Script = Callable[[LlmRequest, int], Step]


def call(tool: str, **arguments: Any) -> Step:
    return ("call", tool, arguments)


def draft(text: str) -> Step:
    return ("text", text, {})


class ScriptedLlm(BaseLlm):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str = "scripted"
    steps: Sequence[Step] | None = None
    script: Script | None = None
    seen: list[LlmRequest] = Field(default_factory=list)
    cursor: int = 0
    delay_s: float = 0.0
    fail_with: str | None = (
        None  # raise this message instead of answering, to script a model outage
    )

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        self.seen.append(llm_request)
        if self.fail_with is not None:
            raise RuntimeError(self.fail_with)
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        index = self.cursor
        self.cursor += 1
        if self.script is not None:
            kind, value, arguments = self.script(llm_request, index)
        elif self.steps and index < len(self.steps):
            kind, value, arguments = self.steps[index]
        else:
            raise RuntimeError("the scripted model has no step left")
        part = (
            Part.from_function_call(name=value, args=arguments)
            if kind == "call"
            else Part.from_text(text=value)
        )
        yield LlmResponse(content=Content(role="model", parts=[part]))
