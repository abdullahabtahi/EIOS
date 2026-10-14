"""Fact flattening (spec 022, research R-2): every numeric leaf of a tool result becomes a labelled fact.

A fact keeps where it came from (`path`), its normalised unit family, the period and look-back windows its
name states (`monthly`, `14d`), and the words that label it: the field path, sibling metric names, and any
per-case aliases. The judge supports a figure only when value, unit and label all agree.
Standard library only; parses under Python 3.12.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .text import content_tokens, raw_tokens

LABEL_KEYS = ("metric_id", "metric", "name", "label", "title", "kpi")
_UNIT_BY_TOKEN: tuple[tuple[str, frozenset[str]], ...] = (
    ("currency", frozenset({"usd", "eur", "gbp", "dollar", "dollars", "euro"})),
    ("percent", frozenset({"pct", "percent", "percentage"})),
    ("bps", frozenset({"bps"})),
    ("multiplier", frozenset({"multiplier", "multiple", "times", "factor"})),
    ("ratio", frozenset({"probability", "hazard", "ratio", "rate", "share", "fraction"})),
    (
        "duration",
        frozenset({"hours", "hour", "hrs", "minutes", "seconds", "days", "latency", "sla"}),
    ),
    (
        "count",
        frozenset(
            {"count", "size", "number", "num", "transfers", "members", "accounts", "tickets"}
        ),
    ),
)
_UNIT_BY_HINT = {
    "usd": "currency", "eur": "currency", "gbp": "currency", "%": "percent", "percent": "percent",
    "pct": "percent", "ratio": "ratio", "bps": "bps", "x": "multiplier", "multiplier": "multiplier",
    "hours": "duration", "hrs": "duration", "days": "duration", "minutes": "duration", "count": "count",
}  # fmt: skip
_PERIOD_BY_TOKEN = {
    "monthly": "month", "month": "month", "weekly": "week", "week": "week", "daily": "day",
    "annual": "year", "yearly": "year", "year": "year",
}  # fmt: skip
_DURATION_BY_TOKEN = {
    "hours": "hour", "hour": "hour", "hrs": "hour", "minutes": "minute", "days": "day", "day": "day",
}  # fmt: skip
_WINDOW = re.compile(r"^(\d+)d$")


@dataclass(frozen=True)
class Fact:
    call_index: int
    path: str
    value: float
    unit: str  # currency, percent, ratio, bps, multiplier, duration, count, other
    period: str | None
    label_tokens: frozenset[str]
    windows: frozenset[int]
    duration_unit: str | None


def _unit_of(tokens: Sequence[str], hint: str | None) -> str:
    if hint and hint.lower() in _UNIT_BY_HINT:
        return _UNIT_BY_HINT[hint.lower()]
    for family, words in _UNIT_BY_TOKEN:
        if words & set(tokens):
            return family
    return "other"


def _make_fact(
    call_index: int,
    parts: Sequence[str],
    value: float,
    labels: Sequence[str],
    hint: str | None,
    aliases: Mapping[str, Sequence[str]],
) -> Fact:
    tokens = [t for part in parts for t in raw_tokens(part)]
    alias_words = [
        w for phrase in aliases.get(_field_name(parts), ()) for w in content_tokens(phrase)
    ]
    label_tokens = {t for part in parts for t in content_tokens(part)}
    label_tokens |= {t for label in labels for t in content_tokens(label)} | set(alias_words)
    named = [*tokens, *(t for label in labels for t in raw_tokens(label))]
    windows = {int(m.group(1)) for t in named if (m := _WINDOW.match(t))}
    return Fact(
        call_index=call_index,
        path=f"{call_index}." + ".".join(parts),
        value=value,
        unit=_unit_of(tokens, hint),
        period=next((_PERIOD_BY_TOKEN[t] for t in tokens if t in _PERIOD_BY_TOKEN), None),
        label_tokens=frozenset(label_tokens),
        windows=frozenset(windows),
        duration_unit=next(
            (_DURATION_BY_TOKEN[t] for t in tokens if t in _DURATION_BY_TOKEN), None
        ),
    )


def _field_name(parts: Sequence[str]) -> str:
    return re.sub(r"\[\d+\]$", "", parts[-1]) if parts else ""


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _walk(
    call_index: int,
    node: Any,
    parts: list[str],
    aliases: Mapping[str, Sequence[str]],
    out: list[Fact],
    inherited_labels: Sequence[str] = (),
    inherited_hint: str | None = None,
) -> None:
    if isinstance(node, dict):
        labels = list(inherited_labels) + [
            str(node[k]) for k in LABEL_KEYS if isinstance(node.get(k), str)
        ]
        raw_hint = node.get("unit")
        hint = raw_hint if isinstance(raw_hint, str) else inherited_hint
        for key, child in node.items():
            direct = _is_number(
                child
            )  # a unit or metric name describes its own sibling values only
            sub_labels, sub_hint = (labels, hint) if direct else ((), None)
            _walk(call_index, child, [*parts, str(key)], aliases, out, sub_labels, sub_hint)
    elif isinstance(node, list):
        for i, child in enumerate(node):
            _walk(call_index, child, [*parts[:-1], f"{parts[-1]}[{i}]"] if parts else [f"[{i}]"], aliases, out,
                  inherited_labels, inherited_hint)  # fmt: skip
    elif _is_number(node):
        out.append(
            _make_fact(call_index, parts, float(node), inherited_labels, inherited_hint, aliases)
        )


def flatten_facts(
    tool_calls: Sequence[Mapping[str, Any]], aliases: Mapping[str, Sequence[str]] | None = None
) -> list[Fact]:
    """Facts from every tool call that returned a result (a call with an error contributes none)."""
    facts: list[Fact] = []
    for index, call in enumerate(tool_calls):
        result = call.get("result")
        if call.get("error") or not isinstance(result, dict):
            continue
        _walk(index, result, [], aliases or {}, facts)
    return facts
