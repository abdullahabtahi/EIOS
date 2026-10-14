"""Structured-mode tests (T019): a record with explicit bindings is verified by value and unit equality."""

from typing import Any

from eios.agent_gates.core.faithfulness import judge


def _record(
    answer: str, path: str, span: tuple[int, int], unit: str = "multiplier"
) -> dict[str, Any]:
    return {
        "answer": answer,
        "question": "q",
        "entity_context": None,
        "tool_calls": [
            {
                "name": "inspect_aml_entity",
                "arguments": {"entity_id": "CR84920"},
                "result": {"discrepancy_multiplier": 16.0, "composite_risk_score": 89},
            }
        ],
        "bindings": [
            {"span": list(span), "fact_ref": {"tool_call_index": 0, "path": path}, "unit": unit}
        ],
    }


def test_a_binding_to_the_right_field_is_supported() -> None:
    answer = "The multiplier is 16.0x."
    start = answer.index("16.0x")
    result = judge(_record(answer, "discrepancy_multiplier", (start, start + 5)))
    assert result.passed
    assert result.counts["supported"] == 1


def test_a_binding_to_the_wrong_field_fails() -> None:
    answer = "The risk score is 16."
    start = answer.index("16")
    result = judge(_record(answer, "composite_risk_score", (start, start + 2), unit="none"))
    assert not result.passed
    assert result.verdicts[0].reason == "binding_mismatch"


def test_a_figure_without_a_binding_is_residue_and_fails() -> None:
    answer = "The multiplier is 16.0x and the ring has 47 members."
    start = answer.index("16.0x")
    result = judge(_record(answer, "discrepancy_multiplier", (start, start + 5)))
    assert not result.passed
    assert any(v.reason == "unbound" for v in result.verdicts)
