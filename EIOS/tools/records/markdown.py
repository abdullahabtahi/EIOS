"""Read-only markdown helpers shared by the ADR, spike and index parsers.

Nothing here validates content. A section or field that is not present is reported as
``ABSENT`` so that it can be told apart from a section that is present but empty (``""``).
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Absent:
    """Marker for a section or field that does not appear in the source text."""

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "ABSENT"


ABSENT = Absent()

type FieldValue = str | Absent


@dataclass(frozen=True)
class Section:
    """A level-two (``## ``) section: its heading text and everything up to the next one."""

    heading: str
    body: str


_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^#{1,6}\s")
_H1 = re.compile(r"^#\s+(?P<text>.+?)\s*$")
_H2 = re.compile(r"^##\s+(?P<text>.+?)\s*$")
_NUMBER_PREFIX = re.compile(r"^\d+\.\s*")
_SEPARATOR_CELL = re.compile(r"^:?-{1,}:?$")
_CELL_SPLIT = re.compile(r"(?<!\\)\|")


def _fence_flags(lines: list[str]) -> list[bool]:
    """True for every line that is inside a fenced code block, delimiters included."""
    flags: list[bool] = []
    inside = False
    for line in lines:
        if _FENCE.match(line):
            flags.append(True)
            inside = not inside
        else:
            flags.append(inside)
    return flags


def first_h1(text: str) -> FieldValue:
    """Text of the first ``# `` heading outside code fences, or ``ABSENT``."""
    lines = text.splitlines()
    for line, fenced in zip(lines, _fence_flags(lines), strict=True):
        match = None if fenced else _H1.match(line)
        if match:
            return match["text"]
    return ABSENT


def split_sections(text: str) -> tuple[Section, ...]:
    """Split a document on ``## `` headings; text before the first one is discarded."""
    lines = text.splitlines()
    sections: list[Section] = []
    heading: str | None = None
    body: list[str] = []
    for line, fenced in zip(lines, _fence_flags(lines), strict=True):
        match = None if fenced else _H2.match(line)
        if match:
            if heading is not None:
                sections.append(Section(heading, "\n".join(body)))
            heading, body = match["text"], []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        sections.append(Section(heading, "\n".join(body)))
    return tuple(sections)


def find_section(sections: tuple[Section, ...], name: str) -> Section | None:
    """First section whose heading equals ``name``, ignoring case and a leading ``N.``."""
    wanted = name.casefold()
    for section in sections:
        if _NUMBER_PREFIX.sub("", section.heading).casefold() == wanted:
            return section
    return None


_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def strip_emphasis(cell: str) -> str:
    """Unwrap markdown links, remove one surrounding ``**`` pair and outer whitespace."""
    text = _LINK.sub(r"\1", cell.strip())
    if len(text) > 4 and text.startswith("**") and text.endswith("**"):
        return text[2:-2].strip()
    return text


def _split_cells(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [cell.strip().replace("\\|", "|") for cell in _CELL_SPLIT.split(inner)]


def _table_blocks(text: str) -> list[list[str]]:
    """Contiguous runs of pipe-prefixed lines outside code fences."""
    lines = text.splitlines()
    blocks: list[list[str]] = []
    current: list[str] = []
    for line, fenced in zip(lines, _fence_flags(lines), strict=True):
        if not fenced and line.lstrip().startswith("|"):
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def parse_table(text: str) -> tuple[dict[str, str], ...]:
    """Rows of the first pipe table in ``text`` keyed by header; ``()`` when there is none.

    Raises ``ValueError`` when a row's cell count differs from the header's.
    """
    for block in _table_blocks(text):
        if len(block) < 2:
            continue
        header = _split_cells(block[0])
        if not all(_SEPARATOR_CELL.match(cell) for cell in _split_cells(block[1])):
            continue
        rows: list[dict[str, str]] = []
        for line in block[2:]:
            cells = _split_cells(line)
            if len(cells) != len(header):
                msg = f"row has {len(cells)} cells, expected {len(header)}: {line.strip()!r}"
                raise ValueError(msg)
            rows.append(dict(zip(header, cells, strict=True)))
        return tuple(rows)
    return ()


def _normalise_label(label: str) -> str:
    return label.lower().replace("-", " ")


def _label_pattern(labels: list[str]) -> re.Pattern[str]:
    ordered = sorted(labels, key=len, reverse=True)
    alternatives = "|".join(
        "[ -]".join(re.escape(w) for w in label.split(" ")) for label in ordered
    )
    return re.compile(
        rf"^(?P<hash>\#{{2,6}}[ \t]+)?(?:\*\*)?(?P<label>{alternatives})(?![A-Za-z0-9])"
        r"(?:\*\*)?[ \t]*(?P<colon>:)?(?:\*\*)?[ \t]*(?P<rest>.*)$",
        re.IGNORECASE,
    )


def _match_label(pattern: re.Pattern[str], line: str) -> tuple[str, str] | None:
    """(normalised label, same-line text) when ``line`` opens a known field, else None.

    A label opens a field when written as a heading (``## Context``) or followed by a colon
    (``Context: ...``, ``**Context:** ...``).
    """
    match = pattern.match(line)
    if match is None:
        return None
    if match["hash"] and (match["colon"] or not match["rest"].strip()):
        return _normalise_label(match["label"]), match["rest"].strip()
    if not match["hash"] and match["colon"]:
        return _normalise_label(match["label"]), match["rest"].strip()
    return None


def extract_fields(text: str, aliases: Mapping[str, tuple[str, ...]]) -> dict[str, FieldValue]:
    """Collect the named fields of a record written as ``Label: value`` or ``## Label``.

    ``aliases`` maps a field name to the labels that introduce it. A field runs until the next
    heading or known label. Every field name is present in the result: ``ABSENT`` when no label
    introduced it, ``""`` when the label is present with no content. Code-fenced text never
    opens a field. When a field is introduced twice, the first occurrence wins.
    """
    by_label = {_normalise_label(a): f for f, labels in aliases.items() for a in labels}
    pattern = _label_pattern(list(by_label))
    lines = text.splitlines()
    collected: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line, fenced in zip(lines, _fence_flags(lines), strict=True):
        opened = None if fenced else _match_label(pattern, line)
        if opened is not None:
            field = by_label[opened[0]]
            current = None if field in collected else collected.setdefault(field, [])
            if current is not None and opened[1]:
                current.append(opened[1])
        elif not fenced and _HEADING.match(line):
            current = None
        elif current is not None:
            current.append(line)
    return {
        field: "\n".join(collected[field]).strip() if field in collected else ABSENT
        for field in aliases
    }
