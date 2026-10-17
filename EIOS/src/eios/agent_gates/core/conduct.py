"""Conduct judging: what a final answer must never show, and what a refusal must still give.

The runtime rejects a draft that narrates its reasoning or reads its rules aloud (`eios.assistant.conduct`); this judge
checks the answer that was actually shown, so a guard that stops working shows up as a failing case. It also holds a
refusal to the instruction's own rule: say why, then say what can be answered instead. Deterministic over the turn
record, so a live run and a re-grade agree. Standard library only; parses under 3.12.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

# A line that opens by narrating a step instead of answering. "Wait," needs its comma or colon so "Wait times rose" passes.
NARRATION = re.compile(
    r"(?im)^\W*(?:wait[,.:!]|hmm\b|okay[,.]?\s+(?:so|let)\b|let me\b|let's\b|i need to\b|i should\b|"
    r"i will (?:now|first)\b|the user (?:is asking|wants|asks)\b|first,?\s+i(?:'ll| will)\b)"
)

# Talk about the rules themselves. "Rule 7 says" is the model reading its instructions aloud.
ABOUT_RULES = re.compile(
    r"(?i)\b(?:(?:my|your|these|the)\s+(?:instructions|rules|system\s+prompt))\b|"
    r"\brule\s+\d+\s+(?:says|states|tells|requires)\b"
)

_REFUSAL_OPENING = re.compile(r"(?i)^\W*i cannot answer that\b")
_NEXT_STEP = re.compile(
    r"(?i)\b(?:i can (?:answer|help|show|check|run|look)|you can|can be run|can answer|instead|try asking|"
    r"ask (?:about|for|me))\b"
)


def judge_conduct(record: Mapping[str, Any], turn: Mapping[str, Any]) -> dict[str, Any]:
    """Why a final answer's conduct fails, without quoting it. `turn` is the golden turn (may be empty)."""
    answer = str(record.get("answer", ""))
    reasons: list[str] = []
    if NARRATION.search(answer):
        reasons.append("the answer narrates its own reasoning")
    if ABOUT_RULES.search(answer):
        reasons.append("the answer talks about its instructions or rules")
    if (turn.get("refusal_required") or _REFUSAL_OPENING.search(answer)) and not _NEXT_STEP.search(
        answer
    ):
        reasons.append("a refusal gave no next step (what can be answered or run instead)")
    lowered = answer.lower()
    missing = [str(m) for m in turn.get("must_mention", []) if str(m).lower() not in lowered]
    if missing:
        reasons.append("the answer does not mention: " + ", ".join(missing))
    return {"passed": not reasons, "reasons": reasons}
