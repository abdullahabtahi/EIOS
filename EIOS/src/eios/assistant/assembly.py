"""Assemble an answer from a model draft so that no figure the model typed can reach an operator (spec 021 FR-001..003).

The draft carries `{{fact:<fact id>}}` placeholders. Each id must be one a tool returned in this very turn, and is
resolved again through the governed port (`FactResolver`) to a value, unit and as-of. After the placeholders are
removed, any number left in the text is a figure the model typed itself and the draft is rejected. The reasons go
back to the model for another attempt; after `MAX_ATTEMPTS` the answer fails closed with no figure at all.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from eios.assistant.answer import Answer, FigureRef
from eios.ontology.auditor.normalizer import MONTH_PATTERN, NumericTokenNormalizer
from eios.ontology.omcp.port.contracts import DataOrigin

MAX_ATTEMPTS = 3
FAIL_CLOSED_TEXT = (
    "I could not put together an answer I can fully support from the governed data, "
    "so I am not showing any figures."
)

_PLACEHOLDER = re.compile(r"\{\{fact:([^{}]*)\}\}")
_NORMALIZER = NumericTokenNormalizer()
# The auditor exempts "March 15, 2026"; the day-first form "15 March 2026" is a date too, so it is exempt here.
_DAY_FIRST_DATE = re.compile(rf"\b\d{{1,2}}\s+{MONTH_PATTERN}(?:\s+\d{{4}})?\b", re.IGNORECASE)


@dataclass(frozen=True)
class TurnFact:
    """A figure a governed tool returned to the model in this turn, with the envelope that qualifies it."""

    fact_id: str
    value: float
    unit: str
    as_of: datetime
    data_origin: DataOrigin


@dataclass(frozen=True)
class Assembled:
    text: str
    figures: tuple[FigureRef, ...]


@dataclass(frozen=True)
class Rejected:
    problems: tuple[str, ...]


# An entity or alert identifier (CR84920, PTR-882, ALT-CR84920) is a name, not a figure: a token that starts with a
# letter and contains a digit. A number that starts with a digit (16x, 40) is never exempt.
_IDENTIFIER = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]*\d[A-Za-z0-9_-]*\b")


def _plain(value: float) -> str:
    return f"{int(value):,}" if value == int(value) else f"{value:,}"


def render_figure(value: float, unit: str) -> str:
    """A figure with its unit, formatted from the governed value only."""
    if unit == "USD":
        return f"${value:,.0f}" if value == int(value) else f"${value:,.2f}"
    if unit == "percent":
        return f"{_plain(value)}%"
    if unit in {"multiplier", "x"}:
        return f"{_plain(value)}x"
    if unit in {"ratio", "score", "count"}:
        return _plain(value)
    return f"{_plain(value)} {unit}"


def _footer(figures: tuple[FigureRef, ...]) -> str:
    if not figures:
        return ""
    stamps = sorted({f.as_of for f in figures})
    as_of = stamps[0].strftime("%Y-%m-%d %H:%M UTC")
    if len(stamps) > 1:
        as_of = f"{as_of} to {stamps[-1].strftime('%Y-%m-%d %H:%M UTC')}"
    origin = (
        "Demo data (fixture), " if any(f.data_origin is DataOrigin.FIXTURE for f in figures) else ""
    )
    return f"\n\n_{origin}as of {as_of}._"


def assemble_draft(
    draft: str,
    *,
    facts: Mapping[str, TurnFact],
) -> Assembled | Rejected:
    if not draft.strip():
        return Rejected(("the draft is empty",))
    problems: list[str] = []
    figures: list[FigureRef] = []
    resolved: dict[str, FigureRef] = {}

    def fill(match: re.Match[str]) -> str:
        fact_id = match.group(1).strip()
        fact = facts.get(fact_id)
        if fact is None:
            problems.append(f"fact id '{fact_id}' was not returned by a tool in this turn")
            return ""
        if fact_id not in resolved:
            ref = FigureRef(
                fact_id=fact_id,
                value=fact.value,
                unit=fact.unit,
                as_of=fact.as_of,
                data_origin=fact.data_origin,
                text=render_figure(fact.value, fact.unit),
            )
            resolved[fact_id] = ref
            figures.append(ref)
        return resolved[fact_id].text

    text = _PLACEHOLDER.sub(fill, draft)
    if "{{" in text or "}}" in text:
        problems.append("a placeholder is malformed; use exactly {{fact:<fact id>}}")
    # Numbers are searched in the draft with every placeholder removed, so a resolved figure is never mistaken for one.
    prose = _IDENTIFIER.sub(" ", _DAY_FIRST_DATE.sub(" ", _PLACEHOLDER.sub(" ", draft)))
    typed = [n.raw_string for n in _NORMALIZER.extract_numbers(prose)]
    if typed:
        problems.append(
            "write no figure yourself, use a {{fact:<id>}} placeholder instead of: "
            + ", ".join(typed)
        )
    if problems:
        return Rejected(tuple(problems))
    shown = tuple(figures)
    return Assembled(text=text.strip() + _footer(shown), figures=shown)


def fail_closed_answer(problems: tuple[str, ...], origin: DataOrigin) -> Answer:
    """No figure, a plain explanation, and the reasons for the audit trail."""
    detail = "; ".join(problems) if problems else "no reason recorded"
    return Answer(
        text=f"{FAIL_CLOSED_TEXT} Please rephrase the question or ask for a specific figure. (Reason: {detail})",
        data_origin=origin,
        attempts=MAX_ATTEMPTS,
    )
