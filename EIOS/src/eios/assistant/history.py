"""What the drafter is told of earlier turns: the questions and the answers the operator saw, and nothing else.

ADK's default is to replay the whole session to the model as its own conversation. Here that replays a draft the
assembler rejected (a figure no tool returned, written by the model as if it had said it) and the placeholder form of a
draft that was accepted (`{{fact:...}}`), neither of which the operator read. The drafter therefore runs with
`include_contents="none"` (ADK then shows it only the current turn: the question and this turn's tool calls and
results) and this module renders the earlier turns from the stored events instead.
"""

from __future__ import annotations

from collections.abc import Sequence

from google.adk.events.event import Event

from eios.assistant.assembler_agent import ANSWER_METADATA_KEY

MAX_ENTRY_CHARS = (
    600  # [ASSUMPTION] enough to recall what was said; a long answer is cut so history stays small
)
HEADER = (
    "Earlier in this conversation, as the operator read it. Treat it as context only: a figure here is not a source, "
    "and may be written again only if a tool returns it in this turn."
)
_ASSISTANT_SUFFIX = (
    "_assistant"  # the author of a failed turn's closing message (runtime._close_thread)
)


def _text(event: Event) -> str:
    if event.content is None:
        return ""
    return "".join(
        p.text or "" for p in event.content.parts or [] if not getattr(p, "thought", False)
    )


def _is_answer(event: Event) -> bool:
    """A reply the operator saw: the assembler's final event, or the plain failure that closes a failed turn."""
    if ANSWER_METADATA_KEY in (event.custom_metadata or {}):
        return True
    return event.author.endswith(_ASSISTANT_SUFFIX) and bool(_text(event))


def _trim(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= MAX_ENTRY_CHARS else flat[: MAX_ENTRY_CHARS - 1].rstrip() + "…"


def _pairs(events: Sequence[Event]) -> list[tuple[str, str]]:
    """(question, answer) for every question that was answered; one still waiting for its answer is left out."""
    pairs: list[tuple[str, str]] = []
    pending: str | None = None
    for event in events:
        if event.author == "user":
            pending = _text(event) or pending
        elif pending is not None and _is_answer(event):
            pairs.append((pending, _text(event)))
            pending = None
    return pairs


def render_history(events: Sequence[Event], keep: int) -> str:
    """The last `keep` answered turns as a short block for the instruction; empty when there is nothing to say."""
    kept = _pairs(events)[-keep:] if keep > 0 else []
    if not kept:
        return ""
    lines = [HEADER]
    for question, answer in kept:
        lines.append(f"Operator: {_trim(question)}")
        lines.append(f"Assistant: {_trim(answer)}")
    return "\n".join(lines)
