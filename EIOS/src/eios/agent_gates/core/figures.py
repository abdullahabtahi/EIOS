"""Figure extraction and normalisation (spec 022, research R-2).

A figure is one atomic numeric claim in an answer: its value in base units, its unit family, an optional
period ("per week"), the precision it states (half of its last digit), and the words around it. Both digit
forms (`$3.8 million`, `16.0x`, `78%`) and spelled-out forms (`three million`, `twenty-three`) are read.
Standard library only; parses under Python 3.12.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .text import (
    DIRECTION_WORDS,
    NUMBER_WORDS,
    SCALES,
    TENS,
    UNITS,
    content_tokens,
)

_MAGNITUDE = {
    "k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6,
    "b": 1e9, "bn": 1e9, "billion": 1e9, "trillion": 1e12,
}  # fmt: skip
_DURATION_UNITS = {
    "hour": "hour", "hours": "hour", "hr": "hour", "hrs": "hour", "minute": "minute", "minutes": "minute",
    "min": "minute", "mins": "minute", "day": "day", "days": "day", "week": "week", "weeks": "week",
    "month": "month", "months": "month", "year": "year", "years": "year",
}  # fmt: skip
_PERIODS = (
    (re.compile(r"\b(?:per|a|each|every)\s+week\b|\bweekly\b", re.I), "week"),
    (re.compile(r"\b(?:per|a|each|every)\s+month\b|\bmonthly\b", re.I), "month"),
    (re.compile(r"\b(?:per|a|each|every)\s+day\b|\bdaily\b", re.I), "day"),
    (re.compile(r"\b(?:per|a|each|every)\s+year\b|\bannual(?:ly)?\b|\byearly\b", re.I), "year"),
)
_NUMBER = re.compile(
    r"(?<![\w.])(?P<sign0>[-−–])?(?P<pre>[$€£]|(?:USD|EUR|GBP)\s?)?(?P<sign>[-−–])?"
    r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
)
_SUFFIX = re.compile(
    r"(?:(?P<mag_a>[kKmMbB])(?![A-Za-z0-9])|\s?(?P<mag_w>thousand|million|billion|trillion|mn|bn)\b)?"
    r"(?P<unit>\s?%|\s?(?:percent|per cent)\b|x\b|\s?times\b|\s?bps\b|\s?basis points?\b"
    r"|[ -]?(?:hours?|hrs?|days?|minutes?|mins?|weeks?|months?|years?)\b"
    r"|\s?(?:dollars?|usd|eur|euros?|gbp)\b)?",
    re.I,
)
_WORD = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)?")
# Words that label a figure are those in its own clause: "the entries is 1,842 and the head sequence is 1,842".
_CLAUSE = re.compile(r"\s(?:and|but|while|whereas)\s|[,;:]")


@dataclass(frozen=True)
class Figure:
    text: str
    start: int
    end: int
    value: float
    tolerance: float
    unit: str  # currency, percent, bps, multiplier, duration, none
    period: str | None
    context: tuple[str, ...]
    sentence: str
    duration_unit: str | None = None
    directional: bool = False
    spelled: bool = False


def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    cuts = [i + len(sep) for sep in (". ", "\n", "; ") if (i := text.rfind(sep, 0, start)) != -1]
    left = max(cuts + [0])
    rights = [i for sep in (". ", "\n", "; ") if (i := text.find(sep, end)) != -1]
    return left, min(rights + [len(text)])


def _classify_unit(prefix: str | None, unit_text: str | None) -> tuple[str, str | None]:
    """Unit family and, for durations, the duration unit."""
    raw = (unit_text or "").strip(" -").lower()
    if prefix or raw in {"dollar", "dollars", "usd", "eur", "euro", "euros", "gbp"}:
        return "currency", None
    if raw in {"%", "percent", "per cent"}:
        return "percent", None
    if raw in {"bps", "basis point", "basis points"}:
        return "bps", None
    if raw in {"x", "times"}:
        return "multiplier", None
    if raw in _DURATION_UNITS:
        return "duration", _DURATION_UNITS[raw]
    return "none", None


def _period_in(window: str) -> str | None:
    for pattern, name in _PERIODS:
        if pattern.search(window):
            return name
    return None


def _make_figure(
    text: str,
    start: int,
    end: int,
    value: float,
    tolerance: float,
    unit: tuple[str, str | None],
    spelled: bool,
) -> Figure:
    left, right = _sentence_bounds(text, start, end)
    before = content_tokens(_CLAUSE.split(text[left:start])[-1])[-8:]
    after = content_tokens(_CLAUSE.split(text[end:right])[0])[:6]
    window = text[max(left, start - 30) : min(right, end + 30)]
    return Figure(
        text=text[start:end].strip(),
        start=start,
        end=end,
        value=value,
        tolerance=tolerance,
        unit=unit[0],
        period=_period_in(window),
        context=tuple(before + after),
        sentence=text[left:right],
        duration_unit=unit[1],
        directional=bool(DIRECTION_WORDS.search(window)),
        spelled=spelled,
    )


def _digit_figures(text: str) -> list[Figure]:
    figures: list[Figure] = []
    for match in _NUMBER.finditer(text):
        num = match.group("num")
        decimals = len(num.split(".")[1]) if "." in num else 0
        suffix = _SUFFIX.match(text, match.end())
        if suffix is None:  # unreachable: every group is optional
            continue
        mag_key = (suffix.group("mag_a") or suffix.group("mag_w") or "").lower()
        multiplier = _MAGNITUDE.get(mag_key, 1.0)
        negative = bool(match.group("sign0") or match.group("sign"))
        value = float(num.replace(",", "")) * multiplier * (-1 if negative else 1)
        unit = _classify_unit(match.group("pre"), suffix.group("unit"))
        end = suffix.end()
        figures.append(
            _make_figure(
                text, match.start(), end, value, 0.5 * 10 ** (-decimals) * multiplier, unit, False
            )
        )
    return figures


def _parse_run(words: Sequence[str]) -> tuple[float, float] | None:
    """Value and tolerance of a run of number words, or None when it is not a figure ("one" alone)."""
    total = current = 0
    tolerance = 0.5
    for word in words:
        if word == "and":
            continue
        if word in UNITS:
            current += UNITS[word]
            tolerance = 0.5
        elif word in TENS:
            current += TENS[word]
            tolerance = 0.5
        else:
            scale = SCALES[word]
            if scale == 100:
                current = max(current, 1) * 100
            else:
                total += max(current, 1) * scale
                current = 0
            tolerance = 0.5 * scale
    if not any(w in UNITS or w in TENS for w in words):
        return None  # a bare scale word ("million") is the tail of a digit figure, not a figure
    if words == ["one"]:
        return None
    return float(total + current), tolerance


def _spelled_figures(text: str) -> list[Figure]:
    figures: list[Figure] = []
    run: list[str] = []
    run_start = run_end = 0

    def flush() -> None:
        nonlocal run
        while run and run[-1] == "and":
            run.pop()
        parsed = _parse_run(run) if run else None
        if parsed:
            suffix = _SUFFIX.match(text, run_end)
            unit = _classify_unit(None, suffix.group("unit") if suffix else None)
            figures.append(_make_figure(text, run_start, run_end, parsed[0], parsed[1], unit, True))
        run = []

    for match in _WORD.finditer(text):
        parts = match.group(0).lower().split("-")
        if all(p in NUMBER_WORDS for p in parts):
            if not run:
                run_start = match.start()
            run.extend(parts)
            run_end = match.end()
        elif parts == ["and"] and run:
            run.append("and")
        else:
            flush()
    flush()
    return figures


def _overlaps(start: int, end: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(start < e and s < end for s, e in spans)


def extract_figures(text: str, masked: Sequence[tuple[int, int]] = ()) -> list[Figure]:
    """All figures in `text`, in order, skipping any that overlap a masked (exempt) span."""
    found = _digit_figures(text) + _spelled_figures(text)
    kept = [f for f in found if not _overlaps(f.start, f.end, masked)]
    return sorted(kept, key=lambda f: f.start)
