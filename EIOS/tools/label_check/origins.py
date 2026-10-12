"""Check ``generator-run:`` and ``eval-report:`` origin references."""

from __future__ import annotations

import posixpath
import re

from tools.label_check.rules import ORIGIN_INCOMPLETE, ORIGIN_PATH

_GENERATOR = re.compile(r"generator-run:")
_EVAL = re.compile(r"eval-report:\s*(\S+)")
_REQUIRED = ("seed=", "revision=", "dataset=")
_REPORTS = "evals/reports/"


def has_origin(unit: str) -> bool:
    return _GENERATOR.search(unit) is not None or _EVAL.search(unit) is not None


def origin_problems(unit: str) -> list[tuple[str, str]]:
    """``(rule_id, message)`` pairs for incomplete generator runs and bad report paths."""
    problems: list[tuple[str, str]] = []
    match = _GENERATOR.search(unit)
    if match:
        missing = [key.rstrip("=") for key in _REQUIRED if key not in unit[match.end() :]]
        if missing:
            problems.append(
                (ORIGIN_INCOMPLETE, f"generator-run origin is missing {', '.join(missing)}")
            )
    for found in _EVAL.finditer(unit):
        path = posixpath.normpath(found.group(1).rstrip(".,;:)]`").lstrip("`"))
        if not path.startswith(_REPORTS):
            problems.append((ORIGIN_PATH, f"eval-report path must be under {_REPORTS}"))
    return problems
