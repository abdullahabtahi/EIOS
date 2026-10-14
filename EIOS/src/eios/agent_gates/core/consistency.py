"""Agreement between an answer and the workstation payload for the same entity (spec 022 FR-026).

For each figure in the answer, find payload fields its own clause names (value and label words, not value
alone). If any of them agrees with the figure, it is consistent; if some are named and none agrees, it is a
disagreement that names both values. A figure about something the screen does not show is not comparable and
is ignored. Standard library only; parses under Python 3.12.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .exempt import find_exempt
from .facts import flatten_facts
from .faithfulness import _coverage, _grounded_identifiers, _overlap, _unit_ok, _value_matches
from .figures import extract_figures


def compare_to_payload(
    record: Mapping[str, Any],
    payload: Mapping[str, Any],
    aliases: Mapping[str, Sequence[str]] | None = None,
) -> list[dict[str, Any]]:
    answer = str(record.get("answer", ""))
    exempt, ungrounded = find_exempt(answer, _grounded_identifiers(record))
    masked = [(s.start, s.end) for s in exempt + ungrounded]
    facts = flatten_facts([{"result": dict(payload)}], aliases)
    disagreements: list[dict[str, Any]] = []
    for fig in extract_figures(answer, masked):
        named = [f for f in facts if _overlap(fig, f) > 0 and _unit_ok(fig, f)]
        if not named or any(_value_matches(fig, f) for f in named):
            continue
        best = max(named, key=lambda f: (_coverage(fig, f), _overlap(fig, f)))
        disagreements.append(
            {
                "answer_text": fig.text,
                "answer_value": fig.value,
                "payload_path": best.path,
                "payload_value": best.value,
            }
        )
    return disagreements
