"""Assemble an answer from a model draft so that no figure the model typed can reach an operator (spec 021 FR-001..003).

The draft carries `{{fact:<fact id>}}` placeholders. Each id must be one a governed tool returned in this very turn;
its value, unit and as-of are the ones that result carried (a second port call could not be made for capabilities that
need more than an entity id, and could disagree with what the model saw). After the placeholders are
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

# A placeholder prints its figure with the unit and currency sign. A model that writes the unit again right after it
# ("{{fact:x}}x", "{{fact:x}} USD") would show "16xx" or "$8,000 USD", so a repeat of the same unit is dropped.
_PLACEHOLDER = re.compile(
    r"\{\{fact:([^{}]*)\}\}(?:(?P<echo>\s?(?:USD|US dollars|dollars|percent|times|x|×|%))(?![A-Za-z0-9]))?"
)
_UNIT_ECHOES = {
    "USD": {"usd", "us dollars", "dollars"},
    "percent": {"%", "percent"},
    "multiplier": {"x", "×", "times"},
    "x": {"x", "×", "times"},
}
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
    source: str


@dataclass(frozen=True)
class Assembled:
    text: str
    figures: tuple[FigureRef, ...]


@dataclass(frozen=True)
class Rejected:
    problems: tuple[str, ...]


# An entity or alert identifier (CR84920, PTR-882, ALT-CR84920, AC1000001) is a name, not a figure. Only the shapes
# the platform issues are exempt: capital-letter prefixes with two or more digits. Currency and asset codes are not
# identifiers, and lowercase or numeric forms (top-10, over-500, risk_87, 16x, 40) are never exempt.
_IDENTIFIER = re.compile(r"\b(?!(?:USDT?|EUR|GBP|BTC|ETH)\d)[A-Z]{1,5}(?:-[A-Z]{1,6})?-?\d{2,}\b")


# The auditor's normalizer exempts any word-hyphen-digits token, so top-10 or over-500 would pass as a name. Platform
# identifiers start with a capital; a lowercase-led hyphen-number is a figure written as a word.
_DISGUISED_FIGURE = re.compile(r"\b[a-z][A-Za-z]*-\d[\d,.]*%?")


# Markdown list numbering ("1. ", "**2.** ", "  - 3) ") names an item's place, it is not a figure. Only a marker at the
# start of a line counts; "it lost about 2. Then" keeps its number.
_LIST_MARKER = re.compile(r"(?m)^[ \t]*(?:[-*>][ \t]+)?\**\d{1,3}[.)]\**[ \t]+")


# A hash chain value or digest (a SHA-256 hex string) is an identifier; its digits are not figures.
_DIGEST = re.compile(r"\b(?:sha-?256:)?[0-9a-fA-F]{12,}\b")


def _where(prose: str, token: str, at: int | None = None) -> str:
    """The typed token with a few words around it, so the model can see which sentence to fix.

    `at` is where the token really is; without it the first look-alike is quoted, which can point the model at
    the wrong sentence (the "2" of a list item instead of the "tier 2" it must remove)."""
    at = prose.find(token) if at is None else at
    if at < 0:
        return token
    context = " ".join(prose[max(0, at - 24) : at + len(token) + 16].split())
    return f"{token} (in '{context}')"


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


def _without_identifiers(prose: str, identifiers: frozenset[str]) -> str:
    """The prose with each identifier a governed result returned this turn removed; longest first, whole tokens only."""
    for name in sorted(identifiers, key=len, reverse=True):
        prose = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", " ", prose)
    return prose


def assemble_draft(
    draft: str,
    *,
    facts: Mapping[str, TurnFact],
    identifiers: frozenset[str] = frozenset(),
) -> Assembled | Rejected:
    if not draft.strip():
        return Rejected(("the draft is empty",))
    problems: list[str] = []
    figures: list[FigureRef] = []
    resolved: dict[str, FigureRef] = {}

    def fill(match: re.Match[str]) -> str:
        fact_id = match.group(1).strip()
        echo = match.group("echo") or ""
        fact = facts.get(fact_id)
        if fact is None:
            problems.append(f"fact id '{fact_id}' was not returned by a tool in this turn")
            return echo
        if fact_id not in resolved:
            ref = FigureRef(
                fact_id=fact_id,
                value=fact.value,
                unit=fact.unit,
                as_of=fact.as_of,
                data_origin=fact.data_origin,
                source=fact.source,
                text=render_figure(fact.value, fact.unit),
            )
            resolved[fact_id] = ref
            figures.append(ref)
        repeated = echo.strip().lower() in _UNIT_ECHOES.get(fact.unit, set())
        return resolved[fact_id].text + ("" if repeated else echo)

    text = _PLACEHOLDER.sub(fill, draft)
    if "{{" in text or "}}" in text:
        problems.append("a placeholder is malformed; use exactly {{fact:<fact id>}}")
    # Numbers are searched in the draft with every placeholder removed, so a resolved figure is never mistaken for one.
    prose = _without_identifiers(
        _DAY_FIRST_DATE.sub(" ", _PLACEHOLDER.sub(" ", draft)), identifiers
    )
    typed = [m.group(0) for m in _DISGUISED_FIGURE.finditer(prose)]
    prose = _DIGEST.sub(" ", _IDENTIFIER.sub(" ", prose))
    prose = _LIST_MARKER.sub("", prose)
    typed = [_where(prose, t) for t in typed]
    typed += [_where(prose, n.raw_string, n.start_char) for n in _NORMALIZER.extract_numbers(prose)]
    if typed:
        problems.append(
            "write no figure yourself, use a {{fact:<id>}} placeholder instead of: "
            + ", ".join(typed)
        )
    if problems:
        return Rejected(tuple(problems))
    shown = tuple(figures)
    return Assembled(text=text.strip() + _footer(shown), figures=shown)


def fail_closed_answer(origin: DataOrigin) -> Answer:
    """No figure and a plain explanation. The reasons quote what the model typed, so they go to the log, not the operator."""
    return Answer(
        text=f"{FAIL_CLOSED_TEXT} Please rephrase the question or ask for a specific figure.",
        data_origin=origin,
        failed_closed=True,
        attempts=MAX_ATTEMPTS,
    )
