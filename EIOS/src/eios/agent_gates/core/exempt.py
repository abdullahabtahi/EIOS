"""The single reviewed list of text that looks numeric but is not a claim about the data (spec 022).

Designed from a taxonomy, not ported from the legacy checker (research R-14). Categories, in priority order:

- date_time        dates, timestamps and clock times
- version          `v1.4.0`, `version 2.3`
- legal_citation   `31 CFR 1020.320`, `Form 111`, `FATF Recommendation 20`, `S.L. 373.01`, `Section 5(a)`
- period_label     `Q3`, `FY2026`, a year after "in", "since", ...
- identifier       `CR84920`, `PTR-882`, exempt only when a tool, the question or the context produced it
- structure_count  the answer counting its own structure (`3 key findings`, `two sources`)
- list_marker      `1.`, `(2)`, `1st`

An identifier-shaped token that nothing produced is NOT exempt: it is returned separately, so an invented
account number cannot hide behind its digits. Standard library only; parses under Python 3.12.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_STRUCTURE_NOUNS = (
    r"(?:findings?|sources?|points?|steps?|items?|reasons?|factors?|sections?|citations?|tools?|checks?"
    r"|options?|actions?|recommendations?|questions?|caveats?|limitations?|bullets?)"
)
_SMALL_WORDS = (
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen"
    r"|sixteen|seventeen|eighteen|nineteen|twenty)"
)
_CITATION_HEADS = (
    r"(?:Section|Sec\.|Article|Art\.|Regulation|Reg\.|Rule|Chapter|Part|Recommendation|Rec\.|Form|Annex"
    r"|Schedule|Directive|Act)"
)

# (category, priority, pattern). Lower priority number wins an overlap.
_PATTERNS: tuple[tuple[str, int, re.Pattern[str]], ...] = (
    ("date_time", 0, re.compile(
        r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?\b"
        r"|\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b"
        r"|\b\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:\s?(?:UTC|GMT|Z|AM|PM|am|pm))?"
        rf"|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTHS}\.?(?:,?\s+\d{{4}})?\b"
        rf"|\b{_MONTHS}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b"
    )),
    ("version", 1, re.compile(r"\bv\d+(?:\.\d+){1,3}\b|\bversion\s+\d+(?:\.\d+){1,3}\b", re.I)),
    ("legal_citation", 2, re.compile(
        r"\b\d{1,3}\s*CFR\s*§?\s*\d+(?:\.\d+)?(?:\([a-zA-Z0-9]+\))*"
        r"|\b\d{1,3}\s*U\.?S\.?C\.?\s*§?\s*\d+(?:\([a-zA-Z0-9]+\))*"
        rf"|\b{_CITATION_HEADS}\s+\d+(?:\.\d+)*(?:\([a-zA-Z0-9]+\))*"
        r"|\bS\.\s?L\.\s?\d+(?:\.\d+)*|\bLegal Notice\s+\d+(?:\s+of\s+\d{4})?|\bSR\s*\d{1,2}-\d{1,2}\b"
    )),
    ("period_label", 3, re.compile(
        r"\bQ[1-4](?:\s+(?:19|20)\d{2})?\b|\bH[12](?:\s+(?:19|20)\d{2})?\b|\b(?:FY|CY)\s?\d{2,4}\b"
        r"|(?<=\bin )(?:19|20)\d{2}\b|(?<=\bof )(?:19|20)\d{2}\b|(?<=\bsince )(?:19|20)\d{2}\b"
        r"|(?<=\bby )(?:19|20)\d{2}\b|(?<=\byear )(?:19|20)\d{2}\b"
    )),
    ("identifier", 4, re.compile(r"\b[A-Za-z][A-Za-z0-9_-]*\d{2,}[A-Za-z0-9_-]*\b")),
    ("structure_count", 5, re.compile(
        rf"\b\d+\s+(?:[A-Za-z-]+\s+){{0,2}}{_STRUCTURE_NOUNS}\b"
        rf"|\b{_SMALL_WORDS}\s+(?:[A-Za-z-]+\s+){{0,2}}{_STRUCTURE_NOUNS}\b", re.I)),
    ("list_marker", 6, re.compile(
        r"(?m)^\s*(?:\d{1,2}[.)]|\(\d{1,2}\))(?=\s)|\(\d{1,2}\)|\b\d+(?:st|nd|rd|th)\b"
    )),
)  # fmt: skip


@dataclass(frozen=True)
class ExemptSpan:
    start: int
    end: int
    category: str
    text: str


def _candidates(text: str) -> list[tuple[int, int, int, str]]:
    found: list[tuple[int, int, int, str]] = []
    for category, priority, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            if match.end() > match.start():
                found.append((priority, match.start(), match.end(), category))
    return found


def _identifier_set(grounded: Iterable[str]) -> frozenset[str]:
    return frozenset(g.lower() for g in grounded)


def find_exempt(
    text: str, grounded: Iterable[str] = ()
) -> tuple[list[ExemptSpan], list[ExemptSpan]]:
    """Exempt spans in `text`, and the identifier-shaped tokens nothing produced (not exempt).

    `grounded` holds the lower-cased identifiers that a tool result, tool argument, the question or the
    entity context contains.
    """
    known = _identifier_set(grounded)
    accepted: list[ExemptSpan] = []
    ungrounded: list[ExemptSpan] = []
    taken: list[tuple[int, int]] = []
    # Longest span wins within a priority; lower priority number wins across categories.
    for _priority, start, end, category in sorted(
        _candidates(text), key=lambda c: (c[0], c[1] - c[2])
    ):
        if any(start < e and s < end for s, e in taken):
            continue
        span = ExemptSpan(start, end, category, text[start:end])
        taken.append((start, end))
        if category == "identifier" and span.text.lower() not in known:
            ungrounded.append(span)
        else:
            accepted.append(span)
    return sorted(accepted, key=lambda s: s.start), sorted(ungrounded, key=lambda s: s.start)
