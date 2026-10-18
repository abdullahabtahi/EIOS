"""Assemble an answer from a model draft so that no figure the model typed can reach an operator (spec 021 FR-001..003).

The draft carries `{{fact:<fact id>}}` placeholders. Each id must be one a governed tool returned in this very turn;
its value, unit and as-of are the ones that result carried (a second port call could not be made for capabilities that
need more than an entity id, and could disagree with what the model saw). A passage of a regulation is shown the
same way, with `{{quote:<passage id>}}`: the text and its page come from the result of this turn, so a deadline or a
threshold in a rule reaches the operator exactly as the regulator wrote it and is never retyped. After the
placeholders are removed, any number left in the text is a figure the model typed itself and the draft is rejected. The reasons go
back to the model for another attempt; after `MAX_ATTEMPTS` the answer fails closed with no figure at all.

Traced mode (`trace_typed=True`, the default of the assistant) relaxes only the last step. A figure the model wrote
itself, "61.67%" or "$1.09M", is shown when a governed tool returned a matching value in this turn, to the precision it
was written at and in the unit it was written in; the answer then cites that value like a placeholder would. A figure
that matches nothing is rejected exactly as before, so nothing reaches an operator without a source, and a correct
answer is no longer sent back only because it was not written as a placeholder.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime

from eios.assistant.answer import Answer, FigureRef, SourceRef
from eios.assistant.conduct import conduct_problems
from eios.assistant.spelled_numbers import spelled_numbers
from eios.knowledge.highlight import body_sentences
from eios.ontology.auditor.normalizer import MONTH_PATTERN, NumericTokenNormalizer
from eios.ontology.omcp.port.contracts import DataOrigin

MAX_ATTEMPTS = (
    2  # one draft and one redraft: a draft that fails twice is not going to be fixed by a third
)
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


@dataclass(frozen=True)
class _Typed:
    """A number the model wrote itself: how it is reported back, and how it was written (to check it against a result)."""

    report: str
    value: float
    decimals: int  # digits after the point as written
    scale: float  # 1, or 1e3 / 1e6 / 1e9 for K, M, B
    symbol: str  # "", "$", "%" or "x"
    # The few words written right after it ("impossible jumps"), to tell equal values apart.
    after: str = ""
    negative: bool = False  # written with a minus directly on it ("-$32,500", "-4.1%")


_SIGNS = "-\u2212"  # a hyphen-minus or a true minus sign


def _signed(prose: str, match: re.Match[str]) -> bool:
    """Is the number written with a minus on it? Only a sign touching the figure counts, and not a dash between
    numbers or words ("3-5", "step-2"), which is a range or a hyphen."""
    for group in ("usd", "int"):
        start = match.start(group)
        if start < 0:
            continue
        if (
            start > 0
            and prose[start - 1] in _SIGNS
            and not (start > 1 and prose[start - 2].isalnum())
        ):
            return True
    return False


_WRITTEN = re.compile(
    r"(?P<usd>\$)?\s*(?P<int>\d[\d,]*)(?:\.(?P<dec>\d+))?\s*"
    r"(?P<suffix>%|pct\b|percent\b|usd\b|dollars?\b|x\b|×|bn\b|billion\b|million\b|thousand\b|[kmb]\b)?",
    re.IGNORECASE,
)
_SCALES = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}


def _written(prose: str, at: int, report: str) -> _Typed | None:
    """Read how the number at `at` was written: its value, decimals, scale suffix and unit symbol."""
    match = _WRITTEN.search(prose, max(0, at))
    if match is None or match.group("int") is None:
        return None
    suffix = (match.group("suffix") or "").lower()
    symbol = (
        "$"
        if match.group("usd")
        or prose[: match.start("int")]
        .rstrip(_SIGNS)
        .endswith("$")  # "$-32,500": the sign sits after the symbol
        or suffix in {"usd", "dollar", "dollars"}
        else "%"
        if suffix in {"%", "pct", "percent"}
        else "x"
        if suffix in {"x", "×"}
        else ""
    )
    scale = _SCALES.get(suffix, 1.0)
    whole, dec = match.group("int").replace(",", ""), match.group("dec") or ""
    after = " ".join(
        _WORD.findall(prose[match.end() : match.end() + _AFTER_CHARS].lower())[:_AFTER_WORDS]
    )
    return _Typed(
        report,
        float(f"{whole}.{dec or '0'}"),
        len(dec),
        scale,
        symbol,
        after,
        _signed(prose, match),
    )


_WORD = re.compile(r"[a-z]+")
_AFTER_CHARS, _AFTER_WORDS = 40, 3


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _named_by(typed: _Typed, fact: TurnFact) -> int:
    """How well the words after a written number name this fact: its unit ("jumps"), or a word of its own name."""
    words = {_stem(w) for w in typed.after.split()}
    if not words:
        return 0
    unit = {_stem(w) for w in _WORD.findall(fact.unit.lower())}
    name = {_stem(w) for w in _WORD.findall(fact.fact_id.rsplit(":", 1)[-1].lower())}
    return 2 * len(words & unit) + len(words & name)


def _typed_numbers(draft: str, identifiers: frozenset[str]) -> list[_Typed | str]:
    """Every figure the model typed itself, as read (or, when it cannot be read, as a report to reject). The draft is
    read with each placeholder removed, so a resolved figure or a quoted passage is never mistaken for one."""
    prose = _without_identifiers(
        _DAY_FIRST_DATE.sub(" ", _PLACEHOLDER.sub(" ", _QUOTE.sub(" ", draft))), identifiers
    )
    disguised = [(m.start(), m.group(0)) for m in _DISGUISED_FIGURE.finditer(prose)]
    prose = _DIGEST.sub(" ", _IDENTIFIER.sub(" ", prose))
    prose = _LIST_MARKER.sub("", _ISO_TIMESTAMP.sub(" ", prose))
    found: list[_Typed | str] = []
    for _, token in disguised:
        report = _where(prose, token)
        at = prose.find(token)
        found.append((at >= 0 and _written(prose, at + (token.find("-") + 1), report)) or report)
    for m in _RANK_LABEL.finditer(prose):
        report = _where(prose, m.group(0), m.start())
        found.append(
            _written(prose, m.start() + len(m.group(0)) - len(m.group(0).split()[-1]), report)
            or report
        )
    for n in _NORMALIZER.extract_numbers(prose):
        report = _where(prose, n.raw_string, n.start_char)
        found.append(_written(prose, n.start_char, report) or report)
    # A number in words is a figure too ("two countries"); checked like digits, so a count cannot slip past RL-1.
    for s in spelled_numbers(prose):
        words = prose[s.start : s.end]
        after = " ".join(_WORD.findall(prose[s.end : s.end + _AFTER_CHARS].lower())[:_AFTER_WORDS])
        found.append(_Typed(_where(prose, words, s.start), s.value, 0, s.scale, s.symbol, after))
    return found


def _typed_figures(draft: str, identifiers: frozenset[str]) -> list[str]:
    """Every figure the model typed itself, reported with the words around it."""
    return [t if isinstance(t, str) else t.report for t in _typed_numbers(draft, identifiers)]


def _near(shown: float, decimals: int, scale: float, candidate: float) -> bool:
    """Does `candidate` round to what was written? 0.62 and 61.67% and $1.09M are all roundings of what a tool returned."""
    tolerance = 0.5 * 10.0**-decimals * scale
    return abs(shown * scale - candidate) <= tolerance * (1 + 1e-9)


def _sign_agrees(typed: _Typed, fact: TurnFact) -> bool:
    """A loss written as a gain is a different claim: the sign written must be the sign returned."""
    return typed.negative == (fact.value < 0)


def _fits(typed: _Typed, fact: TurnFact) -> bool:
    """A typed figure matches a returned fact when the value agrees at the precision written and the unit agrees."""
    unit, value = (
        fact.unit,
        abs(fact.value),
    )  # the sign is checked on its own, and the written value has none
    if not _sign_agrees(typed, fact):
        return False
    if typed.symbol == "$":
        return unit == "USD" and _near(typed.value, typed.decimals, typed.scale, value)
    if typed.symbol == "%":
        return (unit == "percent" and _near(typed.value, typed.decimals, 1.0, value)) or (
            unit == "ratio" and _near(typed.value, typed.decimals, 0.01, value)
        )
    if typed.symbol == "x":
        return unit in {"multiplier", "x"} and _near(
            typed.value, typed.decimals, typed.scale, value
        )
    if not math.isclose(typed.scale, 1.0, abs_tol=1e-9):
        return _near(typed.value, typed.decimals, typed.scale, value)
    return _near(typed.value, typed.decimals, 1.0, value)


def _figure_for(typed: _Typed, fact: TurnFact) -> FigureRef:
    text = typed.report.split(" (in ", 1)[0]
    return FigureRef(
        fact_id=fact.fact_id,
        value=fact.value,
        unit=fact.unit,
        as_of=fact.as_of,
        data_origin=fact.data_origin,
        source=fact.source,
        text=text,
    )


def _trace(
    typed: list[_Typed | str], facts: Mapping[str, TurnFact], numbers: frozenset[float]
) -> tuple[list[FigureRef], list[str]]:
    """Each typed figure against what the tools returned: the figures it cites, and the ones that match nothing.

    A figure with a unit sign ($, %, x, K, M, B) can only match a returned fact of that unit. A bare number may also
    match a number a result held that is not a figure with a unit (days left, a window, a count): it is allowed, and
    has no figure chip because no unit-bearing fact stands behind it."""
    cited: dict[str, FigureRef] = {}
    unmatched: list[str] = []
    for item in typed:
        if isinstance(item, str):
            unmatched.append(item)
            continue
        # Several returned facts can share a value; cite the one the words after the figure name, not the first.
        fitting = [f for f in facts.values() if _fits(item, f)]
        fact = max(fitting, key=lambda f: _named_by(item, f)) if fitting else None
        if fact is not None:
            cited.setdefault(fact.fact_id, _figure_for(item, fact))
        elif not (item.symbol or not math.isclose(item.scale, 1.0, abs_tol=1e-9)) and any(
            _near(item.value, item.decimals, 1.0, n) for n in numbers
        ):
            continue
        else:
            unmatched.append(item.report)
    return list(cited.values()), unmatched


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
    numbers: frozenset[float] = frozenset(),
    trace_typed: bool = False,
    instruction: str = "",
) -> Assembled | Rejected:
    if not draft.strip():
        return Rejected(("the draft is empty",))
    if _SENTINEL in draft:
        return Rejected(("the draft contains a control character",))
    if conduct := conduct_problems(draft, instruction):
        return Rejected(conduct)
    state = _Fill(facts, passages or {})
    text = _PLACEHOLDER.sub(state.fill, _QUOTE.sub(state.mark, draft))
    problems = state.problems
    if "{{" in text or "}}" in text:
        problems.append(
            "a placeholder is malformed; use exactly {{fact:<fact id>}} or {{quote:<passage id>}}"
        )
    traced: list[FigureRef] = []
    if trace_typed:
        traced, unmatched = _trace(_typed_numbers(draft, identifiers), facts, numbers)
        if unmatched:
            problems.append(
                "this figure matches no figure a tool returned this turn; write only figures from tool results "
                "(rounded sensibly) or leave it out: " + ", ".join(unmatched)
            )
    elif typed := _typed_figures(draft, identifiers):
        problems.append(
            "write no figure yourself, use a {{fact:<id>}} placeholder instead of: "
            + ", ".join(typed)
        )
    if problems:
        return Rejected(tuple(problems))
    shown = tuple(dict.fromkeys([*state.figures.values(), *traced]))
    for index, passage in enumerate(state.quoted):
        # The credit line closes a quote, so the full stop the model typed after the placeholder would stand alone.
        mark = re.compile(rf"{_SENTINEL}{index}{_SENTINEL}[ \t]*[.;,]?")
        text = mark.sub(lambda _m, p=passage: render_quote(p), text, count=1)
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
