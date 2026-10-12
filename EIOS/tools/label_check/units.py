"""Split Markdown into claim units: sentences, table rows and list items."""

from __future__ import annotations

import re
from bisect import bisect_right
from collections.abc import Iterator

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_HEADING = re.compile(r"^#{1,6}\s")
_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")
_QUOTE = re.compile(r"^\s*>\s?")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

Unit = tuple[int, str]


def _sentences(buffer: list[Unit]) -> Iterator[Unit]:
    joined = " ".join(text for _, text in buffer)
    starts, offset = [], 0
    for _, text in buffer:
        starts.append(offset)
        offset += len(text) + 1
    begin = 0
    for match in [*_SENTENCE_END.finditer(joined), None]:
        end = match.start() if match else len(joined)
        sentence = joined[begin:end].strip()
        if sentence:
            yield buffer[bisect_right(starts, begin) - 1][0], sentence
        begin = match.end() if match else len(joined)


def _numbered(text: str) -> Iterator[tuple[int, str | None]]:
    """Numbered lines outside fences; a fence boundary is yielded as ``None``."""
    in_fence = False
    for number, raw in enumerate(text.split("\n"), start=1):
        if _FENCE.match(raw):
            in_fence = not in_fence
            yield number, None
        elif not in_fence:
            yield number, raw


def _kind(line: str, in_item: bool) -> str:
    if not line.strip() or (line.lstrip().startswith("|") and _TABLE_SEPARATOR.match(line)):
        return "skip"
    if _HEADING.match(line):
        return "heading"
    if line.lstrip().startswith("|"):
        return "table"
    if _LIST.match(line):
        return "list"
    return "continuation" if in_item and line[:1].isspace() else "text"


def iter_units(text: str) -> Iterator[Unit]:
    """Yield ``(line_number, unit_text)``; fenced code is skipped, line numbers are 1-based."""
    paragraph: list[Unit] = []
    item: list[Unit] = []

    def flush() -> Iterator[Unit]:
        if item:
            yield item[0][0], " ".join(t.strip() if i else t for i, (_, t) in enumerate(item))
            item.clear()
        if paragraph:
            yield from _sentences(paragraph)
            paragraph.clear()

    for number, raw in _numbered(text):
        if raw is None:
            yield from flush()
            continue
        line = _QUOTE.sub("", raw)
        kind = _kind(line, bool(item))
        if kind == "continuation":
            item.append((number, line))
            continue
        yield from flush()
        if kind == "list":
            item.append((number, line))
        elif kind in ("heading", "table"):
            yield number, line
        elif kind == "text":
            paragraph.append((number, line.strip()))
    yield from flush()
