"""Assemble an answer from a model draft so that no figure the model typed can reach an operator (spec 021 FR-001..003).

The draft carries `{{fact:<fact id>}}` placeholders. Each id must be one a governed tool returned in this very turn;
its value, unit and as-of are the ones that result carried (a second port call could not be made for capabilities that
need more than an entity id, and could disagree with what the model saw). A passage of a regulation is shown the
same way, with `{{quote:<passage id>}}`: the text and its page come from the result of this turn, so a deadline or a
threshold in a rule reaches the operator exactly as the regulator wrote it and is never retyped. After the
placeholders are removed, any number left in the text is a figure the model typed itself and the draft is rejected. The reasons go
back to the model for another attempt; after `MAX_ATTEMPTS` the answer fails closed with no figure at all.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime

from eios.assistant.answer import Answer, FigureRef, SourceRef
from eios.knowledge.highlight import body_sentences
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
_QUOTE = re.compile(r"\{\{quote:([^{}#]*)(?:#(s\d{1,3})(?:-(s\d{1,3}))?)?\}\}")
MAX_QUOTED_SENTENCES = 4  # a run longer than this is a page, not an answer
_SENTINEL = "\x00"  # stands in for a quote while the draft is checked, so text from a document is never read as a placeholder
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
class TurnPassage:
    """A passage of a regulation a governed tool returned to the model in this turn."""

    passage_id: str
    document_id: str
    title: str
    jurisdiction: str
    pages: str
    text: str
    data_origin: DataOrigin
    highlight: str = ""  # the sentences that answer the question; printed in the answer, the whole text stays the source


@dataclass(frozen=True)
class Assembled:
    text: str
    figures: tuple[FigureRef, ...]
    sources: tuple[SourceRef, ...] = ()


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


# An ISO date or timestamp ("2026-10-12T00:00:00+00:00") is a date, as the judge reads it; a list line that ends it
# with a colon must not turn its digits into figures.
_ISO_TIMESTAMP = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
)
# "Tier 1" names a rank by a number. The judge counts that digit as a figure, so the draft may not type it.
_RANK_LABEL = re.compile(r"\b(?:tier|level)\s+\d+\b", re.IGNORECASE)


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
    return f"\n\n_as of {as_of}._"


def _without_identifiers(prose: str, identifiers: frozenset[str]) -> str:
    """The prose with each identifier a governed result returned this turn removed; longest first, whole tokens only."""
    for name in sorted(identifiers, key=len, reverse=True):
        prose = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", " ", prose)
    return prose


def _inert(text: str) -> str:
    """Document text as the regulator wrote it, minus control characters. It is shown by a renderer that builds elements
    from text (never HTML or links), so a quote needs no escaping and stays verbatim."""
    return text.replace(_SENTINEL, "").strip()


def render_quote(passage: TurnPassage) -> str:
    body = "\n".join(
        f"> {line}" if line.strip() else ">"
        for line in _inert(passage.highlight or passage.text).splitlines()
    )
    credit = (
        f"> — {_inert(passage.title)}, p. {_inert(passage.pages)} ({_inert(passage.jurisdiction)})"
    )
    return f"\n\n{body}\n{credit}\n\n"


def _typed_figures(draft: str, identifiers: frozenset[str]) -> list[str]:
    """Every figure the model typed itself. The draft is read with each placeholder removed, so a resolved figure or a
    quoted passage is never mistaken for one."""
    prose = _without_identifiers(
        _DAY_FIRST_DATE.sub(" ", _PLACEHOLDER.sub(" ", _QUOTE.sub(" ", draft))), identifiers
    )
    disguised = [m.group(0) for m in _DISGUISED_FIGURE.finditer(prose)]
    prose = _DIGEST.sub(" ", _IDENTIFIER.sub(" ", prose))
    prose = _LIST_MARKER.sub("", _ISO_TIMESTAMP.sub(" ", prose))
    typed = [_where(prose, t) for t in disguised]
    typed += [_where(prose, m.group(0), m.start()) for m in _RANK_LABEL.finditer(prose)]
    typed += [_where(prose, n.raw_string, n.start_char) for n in _NORMALIZER.extract_numbers(prose)]
    return typed


def _sources_of(quoted: list[TurnPassage]) -> tuple[SourceRef, ...]:
    """One source per distinct passage quoted, in order of first appearance."""
    return tuple(
        SourceRef(
            passage_id=p.passage_id,
            document_id=p.document_id,
            title=p.title,
            jurisdiction=p.jurisdiction,
            pages=p.pages,
            text=p.text,
            data_origin=p.data_origin,
        )
        for p in {p.passage_id: p for p in quoted}.values()
    )


class _Fill:
    """What one draft's placeholders resolve to, and the problems met on the way."""

    def __init__(self, facts: Mapping[str, TurnFact], passages: Mapping[str, TurnPassage]) -> None:
        self.facts, self.passages = facts, passages
        self.problems: list[str] = []
        self.figures: dict[str, FigureRef] = {}
        self.quoted: list[TurnPassage] = []

    def mark(self, match: re.Match[str]) -> str:
        passage_id = match.group(1).strip()
        passage = self.passages.get(passage_id)
        if passage is None:
            self.problems.append(
                f"passage id '{passage_id}' was not returned by a tool in this turn"
            )
            return " "
        lines = self._lines(passage, match.group(2), match.group(3))
        if lines is None:
            return " "
        self.quoted.append(replace(passage, highlight="\n".join(lines)))
        return f"{_SENTINEL}{len(self.quoted) - 1}{_SENTINEL}"

    def _lines(self, passage: TurnPassage, first: str | None, last: str | None) -> list[str] | None:
        """The sentences a quote names, each exactly as the document wrote it, or the fallback excerpt when none is named."""
        if first is None:
            return (passage.highlight or passage.text).splitlines()
        sentences = body_sentences(passage.text)
        a, b = int(first[1:]), int((last or first)[1:])
        if not 1 <= a <= b <= len(sentences) or b - a + 1 > MAX_QUOTED_SENTENCES:
            self.problems.append(
                f"{passage.passage_id}: quote sentences s1 to s{len(sentences)}, at most {MAX_QUOTED_SENTENCES} in a row"
            )
            return None
        return sentences[a - 1 : b]

    def fill(self, match: re.Match[str]) -> str:
        fact_id = match.group(1).strip()
        echo = match.group("echo") or ""
        fact = self.facts.get(fact_id)
        if fact is None:
            self.problems.append(f"fact id '{fact_id}' was not returned by a tool in this turn")
            return echo
        if fact_id not in self.figures:
            self.figures[fact_id] = FigureRef(
                fact_id=fact_id,
                value=fact.value,
                unit=fact.unit,
                as_of=fact.as_of,
                data_origin=fact.data_origin,
                source=fact.source,
                text=render_figure(fact.value, fact.unit),
            )
        repeated = echo.strip().lower() in _UNIT_ECHOES.get(fact.unit, set())
        return self.figures[fact_id].text + ("" if repeated else echo)


def assemble_draft(
    draft: str,
    *,
    facts: Mapping[str, TurnFact],
    identifiers: frozenset[str] = frozenset(),
    passages: Mapping[str, TurnPassage] | None = None,
) -> Assembled | Rejected:
    if not draft.strip():
        return Rejected(("the draft is empty",))
    if _SENTINEL in draft:
        return Rejected(("the draft contains a control character",))
    state = _Fill(facts, passages or {})
    text = _PLACEHOLDER.sub(state.fill, _QUOTE.sub(state.mark, draft))
    problems = state.problems
    if "{{" in text or "}}" in text:
        problems.append(
            "a placeholder is malformed; use exactly {{fact:<fact id>}} or {{quote:<passage id>}}"
        )
    if typed := _typed_figures(draft, identifiers):
        problems.append(
            "write no figure yourself, use a {{fact:<id>}} placeholder instead of: "
            + ", ".join(typed)
        )
    if problems:
        return Rejected(tuple(problems))
    shown = tuple(state.figures.values())
    for index, passage in enumerate(state.quoted):
        text = text.replace(f"{_SENTINEL}{index}{_SENTINEL}", render_quote(passage))
    return Assembled(
        text=text.strip() + _footer(shown), figures=shown, sources=_sources_of(state.quoted)
    )


def fail_closed_answer(origin: DataOrigin) -> Answer:
    """No figure and a plain explanation. The reasons quote what the model typed, so they go to the log, not the operator."""
    return Answer(
        text=f"{FAIL_CLOSED_TEXT} Please rephrase the question or ask for a specific figure.",
        data_origin=origin,
        failed_closed=True,
        attempts=MAX_ATTEMPTS,
    )
