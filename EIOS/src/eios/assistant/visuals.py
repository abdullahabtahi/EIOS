"""Tables and charts in an answer: the model names a list a tool returned this turn, the platform draws it from it.

The model never writes a row or a plotted value. A tool result that returns a list of records offers it as a source
(`<tool>.<field>`, listed in the result's `visual_sources`); the drafter writes `{{table:<source>}}` or
`{{chart:<source>}}`; the assembler keeps the placeholder only for a source a tool returned in this turn, takes it out of
the text, and returns the rows exactly as the tool gave them. A name no tool returned sends the draft back, like a figure
no tool returned. Results marked untrusted (text a user or dataset wrote) offer no source.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from eios.assistant.answer import Visual, VisualChart, VisualColumn

MAX_VISUALS = 2  # [ASSUMPTION] more than a pair on one answer is a report, not an answer
MAX_ROWS = 100  # [ASSUMPTION] the longest list a tool offers today is 90 days of history
MAX_COLUMNS = 6  # [ASSUMPTION] what a table in the dossier column can show
MAX_SERIES = 3  # [ASSUMPTION] lines or bars a chart can tell apart
_VISUAL = re.compile(r"\{\{(table|chart):([A-Za-z0-9_.\-]+)\}\}")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_SPACE_BEFORE_PUNCT = re.compile(r"[ \t]+([.,;:!?)])")
_RUNS = re.compile(r"[ \t]{2,}")
_UNIT_WORDS = frozenset({"usd", "pct"})


@dataclass(frozen=True)
class Visuals:
    text: str  # the draft with the placeholders taken out
    visuals: tuple[Visual, ...]
    problems: tuple[str, ...]


def _label(key: str, unit: str | None) -> str:
    words = key.split("_")
    if unit and len(words) > 1 and words[-1].lower() in _UNIT_WORDS:
        words = words[:-1]
    return " ".join(words).strip().capitalize()


def _kind(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return "number"
    return "text" if isinstance(value, str) else None


def _columns(
    field: str, records: list[dict[str, Any]], units: Mapping[str, str]
) -> list[dict[str, Any]]:
    """The first scalar fields of the records, in the order the tool gave them; a field is a number or text by its first value."""
    order: list[str] = []
    kinds: dict[str, str] = {}
    for record in records[:MAX_ROWS]:
        for key, value in record.items():
            if key not in order:
                order.append(key)
            if key not in kinds and (kind := _kind(value)):
                kinds[key] = kind
    columns = []
    for key in order:
        if key not in kinds:
            continue
        unit = units.get(f"{field}[].{key}")
        columns.append({"key": key, "label": _label(key, unit), "kind": kinds[key], "unit": unit})
        if len(columns) == MAX_COLUMNS:
            break
    return columns


def sources_of(
    tool: str, raw: Mapping[str, Any], expanded: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """The lists of records in a tool result, as sources a table or chart may be drawn from; none for untrusted text."""
    if raw.get("untrusted"):
        return {}
    units = raw.get("units") or {}
    fact_ids = expanded.get("fact_ids") or {}
    found: dict[str, dict[str, Any]] = {}
    for field, value in raw.items():
        if not (isinstance(value, list) and value and all(isinstance(r, dict) for r in value)):
            continue
        columns = _columns(field, value, units)
        if not columns:
            continue
        keys = [c["key"] for c in columns]
        records = value[:MAX_ROWS]
        found[f"{tool}.{field}"] = {
            "label": _label(field, None),
            "columns": columns,
            "rows": [{k: r.get(k) for k in keys} for r in records],
            "fact_ids": [
                {k: fact_ids[f"{field}[{i}].{k}"] for k in keys if f"{field}[{i}].{k}" in fact_ids}
                for i in range(len(records))
            ],
            "as_of": raw["as_of"],
            "data_origin": raw["data_origin"],
            "citation": raw["source"],
        }
    return found


def _plan(columns: list[VisualColumn], rows: tuple[dict[str, Any], ...]) -> VisualChart | None:
    text = [c for c in columns if c.kind == "text"]
    numbers = [c for c in columns if c.kind == "number"]
    if len(rows) < 2 or not text or not numbers:
        return None
    unit = next((c.unit for c in numbers if c.unit), None)
    series = [c for c in numbers if c.unit == unit][:MAX_SERIES]
    x = text[0]
    dated = all(
        isinstance(r.get(x.key), str) and _DATE.match(r[x.key])
        for r in rows
        if r.get(x.key) is not None
    )
    return VisualChart(
        type="line" if dated else "bar", x=x.key, y=tuple(c.key for c in series), unit=unit
    )


def _build(kind: str, key: str, source: Mapping[str, Any]) -> Visual | str:
    columns = [VisualColumn(**c) for c in source["columns"]]
    rows = tuple(dict(r) for r in source["rows"])
    chart = None
    if kind == "chart":
        chart = _plan(columns, rows)
        if chart is None:
            return (
                f"a chart of '{key}' needs a text or date column and a number column over at least two rows; "
                "show it as a table instead"
            )
    return Visual(
        kind=kind,  # type: ignore[arg-type]
        source=key,
        label=source["label"],
        columns=tuple(columns),
        rows=rows,
        fact_ids=tuple(dict(f) for f in source["fact_ids"]),
        chart=chart,
        as_of=source["as_of"],
        data_origin=source["data_origin"],
        citation=source["citation"],
    )


def extract(draft: str, sources: Mapping[str, Mapping[str, Any]]) -> Visuals:
    visuals: list[Visual] = []
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for match in _VISUAL.finditer(draft):
        kind, key = match.group(1), match.group(2)
        if (kind, key) in seen:
            continue
        seen.add((kind, key))
        source = sources.get(key)
        if source is None:
            available = ", ".join(sorted(sources)) or "none: no tool returned a list this turn"
            problems.append(
                f"{kind} source '{key}' was not returned by a tool in this turn; use one named in a result's "
                f"visual_sources ({available})"
            )
            continue
        built = _build(kind, key, source)
        if isinstance(built, str):
            problems.append(built)
        else:
            visuals.append(built)
    # More than the answer can carry is a presentation limit, not a proof failure: the first are kept, as map moves are.
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", _RUNS.sub(" ", _VISUAL.sub("", draft)))
    return Visuals(text=text, visuals=tuple(visuals[:MAX_VISUALS]), problems=tuple(problems))
