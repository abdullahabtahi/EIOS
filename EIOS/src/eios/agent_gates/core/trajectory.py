"""Trajectory judging (spec 022, US3): which governed capabilities the runtime used, and how.

Match modes follow Google's Gen AI evaluation: exact, in-order, any-order, plus precision (the share of calls
that were expected or allowed) and recall. A case picks its mode (default any-order) and a precision floor.
A turn also fails on a forbidden capability, on too many rounds, on a missing refusal when one is required,
and on any unsupported figure after a failed or empty tool call. Standard library only; parses under 3.12.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .faithfulness import judge

REFUSAL = re.compile(
    r"insufficient data|cannot (?:answer|provide|share|give)|can't (?:answer|provide)|not able to|unable to"
    r"|unavailable|not available|no data|could not put together|cannot put together"
    r"|cannot run|no tested causal path|data does not show",
    re.IGNORECASE,
)


def _is_subsequence(needle: Sequence[str], haystack: Sequence[str]) -> bool:
    it = iter(haystack)
    return all(any(item == candidate for candidate in it) for item in needle)


def _expected(turn: Mapping[str, Any]) -> list[str]:
    items = sorted(
        turn.get("expected_capabilities", []),
        key=lambda c: (c.get("order_index") is None, c.get("order_index") or 0),
    )
    return [str(c["capability"]) for c in items]


def _metrics(called: list[str], expected: list[str], allowed: set[str]) -> dict[str, Any]:
    relevant = [c for c in called if c in set(expected) | allowed]
    return {
        "exact": called == expected,
        "in_order": _is_subsequence(expected, called),
        "any_order": set(expected) <= set(called),
        "precision": len(relevant) / len(called) if called else 1.0,
        "recall": len(set(expected) & set(called)) / len(set(expected)) if expected else 1.0,
    }


def _failed_call(record: Mapping[str, Any]) -> bool:
    return any(c.get("error") or c.get("result") is None for c in record.get("tool_calls", []))


def judge_turn(record: Mapping[str, Any], turn: Mapping[str, Any]) -> dict[str, Any]:
    called = [str(c["capability"]) for c in record.get("tool_calls", []) if c.get("capability")]
    expected = _expected(turn)
    metrics = _metrics(called, expected, set(turn.get("allowed_extra_capabilities", [])))
    mode = str(turn.get("trajectory_match", "any_order"))
    reasons: list[str] = []
    if not metrics[mode]:
        reasons.append(f"{mode} match failed: expected {expected}, called {called}")
    if metrics["precision"] < float(turn.get("min_precision", 0.8)):
        reasons.append(f"precision {metrics['precision']:.2f} below the floor")
    forbidden = set(called) & set(turn.get("forbidden_capabilities", []))
    if forbidden:
        reasons.append(f"forbidden capability called: {sorted(forbidden)}")
    if int(record.get("rounds", 0)) > int(turn.get("max_rounds", 3)):
        reasons.append("more rounds than the bound")
    answer = str(record.get("answer", ""))
    unsupported = [v for v in judge(record).unsupported()]
    if turn.get("refusal_required") and (not REFUSAL.search(answer) or unsupported):
        reasons.append("a refusal with no figure was required")
    elif _failed_call(record) and unsupported:
        reasons.append("a figure was stated after a failed or empty tool call")
    return {"passed": not reasons, "called": called, "reasons": reasons, **metrics, "mode": mode}
