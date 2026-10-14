"""Trajectory judging (US3): Google's match modes plus precision, forbidden calls, rounds and refusals."""

from typing import Any

from eios.agent_gates.core.trajectory import judge_turn


def _record(
    caps: list[str], answer: str = "ok", rounds: int = 1, tools: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    calls = [{"name": c, "capability": c, "arguments": {}, "result": {"n": 1}} for c in caps]
    return {
        "answer": answer,
        "rounds": rounds,
        "question": "q",
        "entity_context": None,
        "tool_calls": tools or calls,
    }


def _turn(expected: list[str], **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "expected_capabilities": [
            {"capability": c, "order_index": i} for i, c in enumerate(expected)
        ],
        "allowed_extra_capabilities": [],
        "forbidden_capabilities": [],
        "max_rounds": 3,
        "trajectory_match": "any_order",
        "min_precision": 0.8,
        "refusal_required": False,
    }
    return base | extra


def test_exact_in_order_and_any_order_are_distinguished() -> None:
    turn = _turn(["a", "b"])
    assert judge_turn(_record(["a", "b"]), turn)["exact"]
    swapped = judge_turn(_record(["b", "a"]), turn)
    assert swapped["any_order"] and not swapped["in_order"] and not swapped["exact"]
    extra = judge_turn(_record(["a", "x", "b"]), turn)
    assert extra["in_order"] and not extra["exact"]
    assert not judge_turn(_record(["a"]), turn)["any_order"]


def test_precision_counts_calls_that_were_expected_or_allowed() -> None:
    turn = _turn(["a"], allowed_extra_capabilities=["m"])
    assert judge_turn(_record(["a", "m"]), turn)["precision"] == 1.0
    assert judge_turn(_record(["a", "z", "z", "z"]), turn)["precision"] == 0.25
    assert not judge_turn(_record(["a", "z", "z", "z"]), turn)["passed"]


def test_a_forbidden_capability_fails_the_turn() -> None:
    result = judge_turn(
        _record(["a", "action.approve"]), _turn(["a"], forbidden_capabilities=["action.approve"])
    )
    assert not result["passed"]
    assert any("forbidden" in r for r in result["reasons"])


def test_too_many_rounds_fail_the_turn() -> None:
    assert not judge_turn(_record(["a"], rounds=5), _turn(["a"]))["passed"]


def test_the_match_mode_is_a_per_case_setting() -> None:
    swapped = _record(["b", "a"])
    assert judge_turn(swapped, _turn(["a", "b"], trajectory_match="any_order"))["passed"]
    assert not judge_turn(swapped, _turn(["a", "b"], trajectory_match="in_order"))["passed"]


def test_a_required_refusal_needs_a_refusal_and_no_figures() -> None:
    turn = _turn([], refusal_required=True)
    assert judge_turn(_record([], answer="That is insufficient data to answer."), turn)["passed"]
    assert not judge_turn(_record([], answer="Next year revenue will be $5 million."), turn)[
        "passed"
    ]
    assert not judge_turn(_record([], answer="Here is the answer."), turn)["passed"]


def test_missing_data_with_no_refusal_expected_still_cannot_state_a_figure() -> None:
    errored: list[dict[str, Any]] = [
        {
            "name": "t",
            "capability": "a",
            "arguments": {},
            "result": None,
            "error": "DATA_UNAVAILABLE",
        }
    ]
    record = _record([], answer="The score is 89.", tools=errored)
    assert not judge_turn(record, _turn(["a"]))["passed"]
