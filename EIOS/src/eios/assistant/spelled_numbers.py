"""Numbers written in words ("two countries", "three million dollars"), read so the assembler can check them like digits.

A live geo run wrote "logged in from two countries" and "four analytical lenses": counts the model made itself by
counting list items, which RL-1 forbids. The assembler checked only digits, so these reached the reader while the
judge failed them. The rules here are the judge's (`agent_gates/core/figures.py`, `exempt.py`): "one" alone is not a
figure, a bare scale word is the tail of a digit figure, a hyphenated word counts only if every part is a number word
("four-eyes" is not), and an answer counting its own structure ("two sources", "three key findings") is exempt. A test
holds the two readers to the same values.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}  # fmt: skip
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}  # fmt: skip
SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
NUMBER_WORDS = frozenset(UNITS) | frozenset(TENS) | frozenset(SCALES)

_WORD = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")
_STRUCTURE = re.compile(
    r"\s+(?:[A-Za-z-]+\s+){0,2}(?:findings?|sources?|points?|steps?|items?|reasons?|factors?|sections?"
    r"|citations?|tools?|checks?|options?|actions?|recommendations?|questions?|caveats?|limitations?|bullets?)\b",
    re.IGNORECASE,
)
_SMALL = 20  # the judge exempts structure counts written as "one" to "twenty"
_SYMBOL = re.compile(r"\s*(?P<word>percent|pct|dollars?|usd)\b|\s*(?P<sign>%)", re.IGNORECASE)


@dataclass(frozen=True)
class Spelled:
    start: int
    end: int  # end of the number words (a unit word after them is read into `symbol`, not the span)
    value: float  # in units of `scale`: "three million" is 3.0 at scale 1e6
    scale: float  # the precision it was written at: 1 for "twenty-three", 1e6 for "three million"
    symbol: str  # "", "$" or "%"


def _parse(words: list[str]) -> tuple[float, float] | None:
    """Total and precision of a run of number words, or None when it is not a figure."""
    if words == ["one"] or not any(w in UNITS or w in TENS for w in words):
        return None
    total = current = 0
    precision = 1.0
    for word in words:
        if word == "and":  # "three hundred and five"
            continue
        if word in UNITS:
            current += UNITS[word]
            precision = 1.0
        elif word in TENS:
            current += TENS[word]
            precision = 1.0
        elif SCALES[word] == 100:
            current = max(current, 1) * 100
            precision = 100.0
        else:
            total += max(current, 1) * SCALES[word]
            current = 0
            precision = float(SCALES[word])
    return float(total + current), precision


def spelled_numbers(prose: str) -> list[Spelled]:
    found: list[Spelled] = []
    run: list[str] = []
    start = end = 0

    def flush() -> None:
        while run and run[-1] == "and":
            run.pop()
        parsed = _parse(run) if run else None
        run.clear()
        if parsed is None:
            return
        total, precision = parsed
        if total <= _SMALL and math.isclose(precision, 1.0, rel_tol=1e-9, abs_tol=1e-9) and _STRUCTURE.match(prose, end):
            return  # "two sources": the answer counting its own structure (the judge's small words only)
        unit = _SYMBOL.match(prose, end)
        word = (unit.group("word") or "").lower() if unit else ""
        symbol = "%" if unit and (unit.group("sign") or word in {"percent", "pct"}) else ""
        symbol = "$" if word in {"dollar", "dollars", "usd"} else symbol
        found.append(Spelled(start, end, total / precision, precision, symbol))

    for match in _WORD.finditer(prose):
        parts = match.group(0).lower().split("-")
        if all(p in NUMBER_WORDS for p in parts):
            if not run:
                start = match.start()
            run.extend(parts)
            end = match.end()
        elif parts == ["and"] and run:
            run.append("and")
        else:
            flush()
    flush()
    return found
