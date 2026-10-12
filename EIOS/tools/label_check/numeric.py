"""Detect numeric claims in a claim unit."""

from __future__ import annotations

import re

from tools.label_check.rules import LabelRules

_MASKED = (
    re.compile(r"`[^`]*`"),
    re.compile(r"\]\([^)]*\)"),
    re.compile(r"https?://\S+"),
    re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+"),
    re.compile(r"^#{1,6}\s+(?:\d+(?:\.\d+)*\.?\s+)?"),
)
_PERCENT = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?\s?(?:%|percent\b)")
_CURRENCY = re.compile(r"[$€£]\s?\d|\d[\d,.]*\s?(?:USD|EUR|GBP)\b")
_RATIO = re.compile(r"(?<![\w.])\d+\s?(?::|in|out of)\s?\d+\b")


def _blank(match: re.Match[str]) -> str:
    return " " * len(match.group(0))


def mask(text: str, rules: LabelRules) -> str:
    """Blank out code, links, identifiers and list or heading numbering, keeping offsets."""
    for pattern in (*_MASKED, *rules.non_claim):
        text = pattern.sub(_blank, text)
    return text


def numeric_claim_kinds(text: str, rules: LabelRules) -> frozenset[str]:
    """Kinds of numeric claim in ``text``: percentage, currency, count, duration, ratio."""
    masked = mask(text, rules)
    checks = {
        "percentage": _PERCENT,
        "currency": _CURRENCY,
        "count": rules.count_pattern,
        "duration": rules.duration_pattern,
        "ratio": _RATIO,
    }
    return frozenset(kind for kind, pattern in checks.items() if pattern.search(masked))
