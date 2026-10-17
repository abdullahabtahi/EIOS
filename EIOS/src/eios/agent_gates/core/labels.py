"""Names a tool returned are names, not figures (spec 022).

An answer that copies a product, gateway or rule name verbatim ("Boom 1000", "Central Payment Gateway #007",
"Refuter Placebo Threshold p > 0.05", "Zero LLM Metric Calculation") carries digits or number words that are part of the
name. The live baseline of 2026-10-17 failed eight cases on these. A string a tool result holds is exempt only when it is
a short label: two to six words, no percent or currency sign, so a sentence or a quantity a tool returned is still
judged as figures. Standard library only; parses under Python 3.12.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

MIN_WORDS, MAX_WORDS, MAX_CHARS = 2, 6, 60
_QUANTITY_SIGNS = re.compile(r"[%$€£]")


def _strings(node: Any) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, Mapping):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, Sequence) and not isinstance(node, (bytes, str)):
        for value in node:
            yield from _strings(value)


def _is_label(text: str) -> bool:
    words = text.split()
    return (
        MIN_WORDS <= len(words) <= MAX_WORDS
        and len(text) <= MAX_CHARS
        and not _QUANTITY_SIGNS.search(text)
    )


def label_spans(answer: str, tool_calls: Sequence[Mapping[str, Any]]) -> list[tuple[int, int]]:
    """Spans of the answer that repeat a short label a tool result returned, matched case-insensitively."""
    labels = {
        s.strip()
        for call in tool_calls
        for s in _strings(call.get("result"))
        if _is_label(s.strip())
    }
    spans: list[tuple[int, int]] = []
    for label in sorted(labels, key=len, reverse=True):
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])", re.IGNORECASE)
        spans += [
            (m.start(), m.end())
            for m in pattern.finditer(answer)
            if not any(m.start() < e and s < m.end() for s, e in spans)
        ]
    return sorted(spans)
