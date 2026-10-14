"""The ADK agent that turns the drafter's text into the operator's answer (spec 021 FR-001..003, FR-013).

It runs after the drafter inside a `LoopAgent` bounded at `MAX_ATTEMPTS`. A rejected draft sends the reasons back to
the drafter through turn state; an accepted one, or the third rejection, ends the loop with a final event whose
`custom_metadata` carries the structured `Answer`. Only these events are shown to the operator, never the draft.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from eios.assistant.answer import Answer
from eios.assistant.assembly import (
    MAX_ATTEMPTS,
    Assembled,
    TurnFact,
    assemble_draft,
    fail_closed_answer,
)
from eios.assistant.tools import FACTS_KEY, IDENTIFIERS_KEY, ORIGINS_KEY, PROPOSALS_KEY, SOURCES_KEY
from eios.llm_gateway.providers.adk_types import Content, Part
from eios.ontology.omcp.port.contracts import DataOrigin

DRAFT_KEY = "temp:draft"
ATTEMPT_KEY = "temp:assembly_attempts"
FEEDBACK_KEY = "temp:assembly_feedback"
ANSWER_METADATA_KEY = "answer"
logger = logging.getLogger(__name__)


def _origin(values: list[str]) -> DataOrigin:
    return (
        DataOrigin.LIVE
        if values and all(v == DataOrigin.LIVE.value for v in values)
        else DataOrigin.FIXTURE
    )


def _turn_facts(raw: dict[str, Any]) -> dict[str, TurnFact]:
    """The facts of this turn; one that cannot be read is dropped, so it is simply "not returned" and cannot be shown."""
    facts: dict[str, TurnFact] = {}
    for fact_id, item in raw.items():
        try:
            facts[fact_id] = _turn_fact(fact_id, item)
        except KeyError, TypeError, ValueError:
            logger.warning("dropping an unreadable turn fact: %s", fact_id)
    return facts


def _turn_fact(fact_id: str, raw: dict[str, Any]) -> TurnFact:
    return TurnFact(
        fact_id=fact_id,
        value=float(raw["value"]),
        unit=raw["unit"],
        as_of=datetime.fromisoformat(raw["as_of"]),
        data_origin=DataOrigin(raw["data_origin"]),
        source=raw["source"],
    )


def final_event(author: str, answer: Answer, *, escalate: bool = True) -> Event:
    return Event(
        author=author,
        content=Content(role="model", parts=[Part.from_text(text=answer.text)]),
        custom_metadata={ANSWER_METADATA_KEY: answer.model_dump(mode="json")},
        actions=EventActions(escalate=escalate),
    )


class AnswerAssembler(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event]:
        state = ctx.session.state
        attempt = int(state.get(ATTEMPT_KEY, 0)) + 1
        origin = _origin(list(state.get(ORIGINS_KEY, [])))
        result = assemble_draft(
            str(state.get(DRAFT_KEY, "")),
            facts=_turn_facts(state.get(FACTS_KEY, {})),
            identifiers=frozenset(state.get(IDENTIFIERS_KEY, [])),
        )
        if isinstance(result, Assembled):
            answer = Answer(
                text=result.text,
                figures=result.figures,
                citations=tuple(dict.fromkeys(state.get(SOURCES_KEY, []))),
                proposed_actions=tuple(state.get(PROPOSALS_KEY, [])),
                data_origin=origin,
                attempts=attempt,
            )
            yield final_event(self.name, answer)
        elif attempt >= MAX_ATTEMPTS:
            logger.warning(
                "answer failed closed after %s attempts: %s", attempt, "; ".join(result.problems)
            )
            yield final_event(self.name, fail_closed_answer(origin))
        else:
            feedback = "; ".join(result.problems)
            logger.info("draft %s rejected: %s", attempt, feedback[:300])
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={ATTEMPT_KEY: attempt, FEEDBACK_KEY: feedback}),
            )
