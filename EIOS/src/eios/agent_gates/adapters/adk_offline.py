"""An offline stand-in for the language model that follows the 022 reference routes (spec 021, judging without a model).

It lets the real ADK runner, tools, sessions, assembler and screening run in CI. It is not the agent's intelligence:
it routes by the same explicit rules as the `toolport` runtime and drafts only placeholders and fixed words, so what
an offline run shows is that the runtime plumbing is sound, never how well a model answers (that is the live run).
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from pydantic import ConfigDict

from eios.agent_gates.adapters.toolport_render import REFUSAL
from eios.agent_gates.adapters.toolport_routes import extract, plan
from eios.llm_gateway.providers.adk_types import Content, Part, text_of

_SCALAR_PATH = re.compile(r"^[a-z0-9_]+$")


def _label(path: str) -> str:
    return " ".join("month" if word == "30d" else word for word in path.split("_"))


class RuleLlm(BaseLlm):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str = "offline-rules"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        question, responses = _turn(llm_request)
        offered = set(llm_request.tools_dict)
        found = extract(question, _context(llm_request))
        for name, payload in responses:
            found.results[name] = payload
        ready = [
            (tool, args)
            for tool, args_fn in plan(question)
            if tool in offered
            and tool not in found.results
            and (args := args_fn(found)) is not None
        ]
        if ready:  # every call whose arguments are known now goes out together, as a model would
            parts = [Part.from_function_call(name=tool, args=args) for tool, args in ready]
            yield LlmResponse(content=Content(role="model", parts=parts))
            return
        yield LlmResponse(
            content=Content(role="model", parts=[Part.from_text(text=_draft(responses))])
        )


def _turn(request: LlmRequest) -> tuple[str, list[tuple[str, dict[str, Any]]]]:
    """The latest user question and the tool results received since it (this turn only)."""
    contents = request.contents or []
    start = max((i for i, c in enumerate(contents) if c.role == "user" and text_of(c)), default=0)
    question = text_of(contents[start]) if contents else ""
    responses: list[tuple[str, dict[str, Any]]] = []
    for content in contents[start + 1 :]:
        for part in content.parts or []:
            if part.function_response is not None:
                responses.append(
                    (str(part.function_response.name), dict(part.function_response.response or {}))
                )
    return question, responses


def _context(request: LlmRequest) -> dict[str, Any]:
    instruction = str(request.config.system_instruction) if request.config else ""
    match = re.search(r"Entity on screen: ([^.\s]+)\.", instruction)
    return {"entity_id": match.group(1)} if match else {}


def _quoted(payload: dict[str, Any]) -> str:
    """A regulation result is shown by quoting its best passage; with no passage the draft says the corpus has no support."""
    passages = payload.get("passages") or []
    first = next((p for p in passages if isinstance(p, dict) and p.get("passage_id")), None)
    if first is None:
        return "The regulatory corpus has nothing that supports an answer to this question."
    return f"The most relevant passage of the regulatory corpus:\n\n{{{{quote:{first['passage_id']}}}}}"


def _draft(responses: list[tuple[str, dict[str, Any]]]) -> str:
    lines: list[str] = []
    for name, payload in responses:
        title = name.replace("_", " ").capitalize()
        error = payload.get("error")
        if not error and payload.get("capability") == "knowledge.regulation":
            lines.append(_quoted(payload))
            continue
        if error:
            message = error.get("message", "unavailable") if isinstance(error, dict) else str(error)
            lines.append(f"{title}: {message}")
            continue
        figures = [
            f"{_label(path)}: {{{{fact:{fact_id}}}}}"
            for path, fact_id in (payload.get("fact_ids") or {}).items()
            if _SCALAR_PATH.match(path)
        ]
        lines.append(
            f"{title}: " + "; ".join(figures) if figures else f"{title}: no figures returned."
        )
    return "\n".join(lines) if lines else REFUSAL
