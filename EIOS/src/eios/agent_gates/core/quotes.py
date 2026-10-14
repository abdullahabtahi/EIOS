"""A quoted passage of a regulation is not a claim about the data, when a tool returned that exact text.

The assembler prints a passage from a `search_regulations` result as a block of `> ` lines followed by a credit line
`> — Title, p. 41-42 (MT)`. A figure inside such a block (a deadline, a threshold, a page) is the regulator's own text.
It is exempt from the figure check only when the block's text is made of lines of a passage of a tool result in the same turn and its
credit line names that passage's document, pages and jurisdiction. A block that does not match is judged like any other
text, so an invented quotation cannot hide its numbers. Standard library only; parses under Python 3.12.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_BLOCK = re.compile(r"(?:^[ \t]*>[^\n]*(?:\n|$))+", re.MULTILINE)
MIN_QUOTE_CHARS = 12  # a slice shorter than this proves nothing
_CREDIT = re.compile(r"^— (?P<title>.+), p\. (?P<pages>\S+) \((?P<jurisdiction>[^)]+)\)$")


def _squash(text: str) -> str:
    return " ".join(text.split())


_SENTENCE_REF = re.compile(r"^s\d+:\s*")


def _passage_text(passage: Mapping[str, Any]) -> str:
    """What a passage says: its text, or (when the record holds the model's view) its numbered sentences."""
    if isinstance(passage.get("text"), str):
        return str(passage["text"])
    return " ".join(_SENTENCE_REF.sub("", str(x)) for x in passage.get("sentences") or [])


def _passages(tool_calls: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = []
    for call in tool_calls:
        result = call.get("result")
        items = result.get("passages") if isinstance(result, Mapping) else None
        if isinstance(items, list):
            found += [p for p in items if isinstance(p, Mapping) and _passage_text(p).strip()]
    return found


def verified_quotes(answer: str, tool_calls: Sequence[Mapping[str, Any]]) -> list[tuple[int, int]]:
    """Character spans of the answer's quote blocks that a tool result of the turn vouches for."""
    passages = _passages(tool_calls)
    if not passages:
        return []
    spans: list[tuple[int, int]] = []
    for block in _BLOCK.finditer(answer):
        lines = [re.sub(r"^[ \t]*>[ \t]?", "", line) for line in block.group(0).splitlines()]
        credit = _CREDIT.match(lines[-1].strip()) if lines else None
        if credit is None:
            continue
        body = [_squash(line).removesuffix("…").rstrip() for line in lines[:-1] if line.strip()]
        if not body or any(len(line) < MIN_QUOTE_CHARS for line in body):
            continue
        for passage in passages:
            whole = _squash(_passage_text(passage))
            if (
                all(line in whole for line in body)
                and str(passage.get("title", "")).strip() == credit["title"]
                and str(passage.get("pages", "")) == credit["pages"]
                and str(passage.get("jurisdiction", "")) == credit["jurisdiction"]
            ):
                spans.append((block.start(), block.end()))
                break
    return spans
