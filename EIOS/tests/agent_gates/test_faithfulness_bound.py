"""A look-back window a field name states is not a figure to bind, in structured mode as in free text.

Found by the first live run of the ADK assistant: "Realized 30-day volume: $1,240,000" bound the dollar figure to
`realized_volume_30d_usd` and the judge then called "30-day" unbound, though the unbound-mode judge accepts it.
"""

from typing import Any

from eios.agent_gates.core.faithfulness import judge

ANSWER = "Realized 30-day volume: $1,240,000"


def _record(path: str) -> dict[str, Any]:
    start = ANSWER.index("$1,240,000")
    return {
        "answer": ANSWER,
        "question": "q",
        "entity_context": None,
        "tool_calls": [
            {
                "name": "get_partner",
                "arguments": {"entity_id": "PTR-882"},
                "result": {path: 1240000.0},
            }
        ],
        "bindings": [
            {
                "span": [start, start + 10],
                "fact_ref": {"tool_call_index": 0, "path": path},
                "unit": "USD",
            }
        ],
    }


def test_a_window_the_field_name_states_is_not_unbound() -> None:
    result = judge(_record("realized_volume_30d_usd"))
    assert result.passed, result.counts


def test_a_window_the_field_name_does_not_state_still_fails() -> None:
    result = judge(_record("realized_volume_usd"))
    assert not result.passed
    assert [v.reason for v in result.verdicts if v.verdict == "unsupported"] == ["unbound"]
