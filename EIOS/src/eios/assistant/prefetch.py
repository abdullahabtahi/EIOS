"""Run the obvious tool before the model's first turn, so a typical question needs one model call instead of two.

Without this the model spends its first call deciding which tool to call (4 to 11 s on the shared endpoint, for about
25 tokens of output) and its second call writing the answer. For the questions where the tool is not in doubt (a
regulation question, a question about the account or partner on screen, the morning briefing) the platform calls the same
governed tool itself and puts the call and its result in the conversation, exactly where the model's own call would be.
The model then drafts straight away, and can still call any tool it needs.

A wrong guess costs a tool call and some context, never a wrong answer: the result passes through the same port, the same
fact ids and the same assembler. Only tools the verified principal is offered are ever run.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from eios.assistant.intent import is_broad
from eios.assistant.tools import (
    FACTS_KEY,
    IDENTIFIERS_KEY,
    NUMBERS_KEY,
    ORIGINS_KEY,
    PASSAGES_KEY,
    PROPOSALS_KEY,
    SOURCES_KEY,
    record_result,
)
from eios.llm_gateway.providers.adk_types import platform_tool_call, platform_tool_result, text_of
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.service import GovernedToolPort

PREFETCH_KEY = "temp:prefetched"  # set once the step has run in this turn, so a retried draft does not repeat it
PLATFORM_CALL = (
    "platform_call"  # event metadata: this tool call was made by the platform, not by a model call
)
DRAFTER = "drafter"  # the events must be the drafter's own, or ADK shows them to it as another agent's message
_MAX_QUERY = 300

_REGULATION = re.compile(
    r"\b(?:regulat\w*|guideline\w*|circular|fiau|pmlftr|labuan|mlro|reporting officer|red.?flags?|"
    r"record.?keeping|keep(?:ing)? records|retention|tipping.?off|politically exposed|due diligence|"
    r"suspicious (?:transaction|activity) reports?)\b",
    re.IGNORECASE,
)
_JURISDICTION = (
    ("MT", re.compile(r"\b(?:malta|maltese|fiau|pmlftr)\b", re.IGNORECASE)),
    ("LB", re.compile(r"\blabuan\b", re.IGNORECASE)),
    ("US", re.compile(r"\b(?:fincen|united states)\b", re.IGNORECASE)),
)
_BRIEFING = re.compile(r"\bbriefing\b|\bbrief me\b", re.IGNORECASE)
_ACCOUNT = re.compile(r"^CR\d{4,6}$", re.IGNORECASE)
_PARTNER = re.compile(r"^(?:PTR|AP|P)-\d{2,5}$", re.IGNORECASE)

Step = tuple[str, dict[str, Any]]


def plan(workstation: Workstation, question: str, entity_id: str | None) -> list[Step]:
    """The tool calls worth making before the model speaks, for this question on this workstation."""
    steps: list[Step] = []
    if workstation in {
        Workstation.AML_INVESTIGATOR,
        Workstation.COMPLIANCE_AUDITOR,
    } and _REGULATION.search(question):
        args: dict[str, Any] = {"query": question.strip()[:_MAX_QUERY]}
        for code, pattern in _JURISDICTION:
            if pattern.search(question):
                args["jurisdiction"] = code
        steps.append(("search_regulations", args))
    elif workstation is Workstation.AML_INVESTIGATOR and entity_id and _ACCOUNT.match(entity_id):
        steps.append(("get_aml_dossier", {"entity_id": entity_id}))
    elif workstation is Workstation.PARTNER_MANAGER and entity_id and _PARTNER.match(entity_id):
        steps.append(("get_partner_signals", {"entity_id": entity_id}))
        if is_broad(
            question
        ):  # the full picture: the integrity check runs in parallel, costing no model call
            steps.append(("get_partner_integrity", {"entity_id": entity_id}))
    elif workstation is Workstation.EXECUTIVE and _BRIEFING.search(question):
        steps.append(("get_briefing", {}))
    return steps


class Prefetcher(BaseAgent):
    """First step of the loop: run the planned tools, emit their call and result as the drafter's own history."""

    port: Any
    principal: Any

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event]:
        state = ctx.session.state
        if state.get(PREFETCH_KEY):
            return
        port: GovernedToolPort = self.port
        principal: Principal = self.principal
        offered = {spec.name: spec for spec in port.list_tools(principal)}
        question = text_of(ctx.user_content)
        steps = [
            (t, a)
            for t, a in plan(principal.workstation, question, state.get("entity_id"))
            if t in offered
        ]
        staged = _Defaulting(
            {
                k: state.get(k)
                for k in (
                    FACTS_KEY,
                    PASSAGES_KEY,
                    SOURCES_KEY,
                    ORIGINS_KEY,
                    IDENTIFIERS_KEY,
                    NUMBERS_KEY,
                    PROPOSALS_KEY,
                )
            }
        )
        outcomes = await asyncio.gather(
            *(asyncio.to_thread(port.call, principal, tool, dict(args)) for tool, args in steps)
        )
        for index, ((tool, args), outcome) in enumerate(zip(steps, outcomes, strict=True)):
            call_id = f"prefetch-{index}-{tool}"
            payload = record_result(staged, offered[tool], outcome, args)
            yield Event(
                author=DRAFTER,
                content=platform_tool_call(tool, args, call_id),
                custom_metadata={PLATFORM_CALL: True},
            )
            yield Event(
                author=DRAFTER,
                content=platform_tool_result(tool, payload, call_id),
                custom_metadata={PLATFORM_CALL: True},
            )
        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    **{k: v for k, v in staged.items() if v is not None},
                    PREFETCH_KEY: True,
                }
            ),
        )


class _Defaulting(dict[str, Any]):
    """Turn state as `record_result` reads it: a key the session does not hold yet reads as empty, not as missing."""

    _EMPTY: dict[str, Any] = {
        FACTS_KEY: {},
        PASSAGES_KEY: {},
        SOURCES_KEY: [],
        ORIGINS_KEY: [],
        IDENTIFIERS_KEY: [],
        NUMBERS_KEY: [],
        PROPOSALS_KEY: [],
    }

    def get(self, key: str, default: Any = None) -> Any:
        value = super().get(key)
        return value if value is not None else self._EMPTY.get(key, default)
