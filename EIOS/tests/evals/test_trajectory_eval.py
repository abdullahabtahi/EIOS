"""Tests for OMCP Tool Trajectory Evaluator & Supervisory Router (T047)."""

from eios.evals.models import ExpectedToolCall, GoldenDialogueTurn
from evals.golden.trajectory_eval import (
    evaluate_turn_trajectory,
    score_supervisory_router_accuracy,
)


def test_trajectory_eval_correct_flow():
    turn = GoldenDialogueTurn(
        turn_index=1,
        user_query="Investigate SAR candidate tok_usr_12",
        expected_route="SentinelAML",
        expected_tool_calls=[
            ExpectedToolCall(tool_name="get_entity_profile", order_index=0),
            ExpectedToolCall(tool_name="get_transaction_history", order_index=1),
        ],
        forbidden_tool_calls=["execute_db_write"],
    )

    res = evaluate_turn_trajectory(
        turn=turn,
        executed_route="SentinelAML",
        executed_tool_calls=["get_entity_profile", "get_transaction_history"],
        agent_response="Profile loaded. Entity shows anomalous deposit pattern.",
    )
    assert res["router_correct"] is True
    assert res["trajectory_valid"] is True
    assert res["redundant_calls_count"] == 0
    assert res["forbidden_calls_count"] == 0


def test_trajectory_eval_penalizes_redundant_calls():
    turn = GoldenDialogueTurn(
        turn_index=1,
        user_query="Fetch latest partner status",
        expected_route="ChurnRadar",
        expected_tool_calls=[ExpectedToolCall(tool_name="get_partner_status", order_index=0)],
    )

    # Redundant execution of same tool
    res = evaluate_turn_trajectory(
        turn=turn,
        executed_route="ChurnRadar",
        executed_tool_calls=["get_partner_status", "get_partner_status", "get_partner_status"],
        agent_response="Partner status retrieved.",
    )
    assert res["redundant_calls_count"] == 2
    assert res["trajectory_valid"] is False


def test_unanswerable_refusal_checked():
    turn = GoldenDialogueTurn(
        turn_index=1,
        user_query="What will the exact competitor revenue be in 2035?",
        expected_route="Synthesis",
        refusal_required=True,
    )

    # Compliant refusal
    res_compliant = evaluate_turn_trajectory(
        turn=turn,
        executed_route="Synthesis",
        executed_tool_calls=[],
        agent_response="Insufficient data available to project competitor revenue to 2035.",
    )
    assert res_compliant["refusal_valid"] is True

    # Hallucinatory non-refusal
    res_non_compliant = evaluate_turn_trajectory(
        turn=turn,
        executed_route="Synthesis",
        executed_tool_calls=[],
        agent_response="Competitor revenue will be exactly $4.5 billion.",
    )
    assert res_non_compliant["refusal_valid"] is False


def test_supervisory_router_accuracy_meets_target():
    # 20 routed turns, 19 correct (95% >= 95% target)
    routes = (
        [("SentinelAML", "SentinelAML")] * 10
        + [("Synthesis", "Synthesis")] * 9
        + [("Synthesis", "ChurnRadar")]
    )
    acc, target_met = score_supervisory_router_accuracy(routes)
    assert acc == 0.95
    assert target_met is True
