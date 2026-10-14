"""Any runtime is judged by the same gates (US6): a trivial stand-in fails for the right reasons."""

from eios.agent_gates.adapters.standin import AlwaysAnswerStandin
from eios.agent_gates.core.faithfulness import judge
from eios.agent_gates.core.trajectory import judge_turn
from eios.agent_gates.port import TurnRequest, run_with_deadline
from eios.agent_gates.records import Outcome, Role, to_agents_cli_case


def _request() -> TurnRequest:
    return TurnRequest(
        question="What is the discrepancy for CR84920?",
        role=Role.AML_INVESTIGATOR,
        operator_id="tok_op_1",
        session_id="s",
    )


def test_the_always_42_standin_fails_faithfulness_and_trajectory_for_the_right_reasons() -> None:
    record = run_with_deadline(AlwaysAnswerStandin("42"), _request())
    assert record.outcome is Outcome.COMPLETED
    data = record.to_json_dict()
    verdict = judge(data)
    assert not verdict.passed and verdict.unsupported()[0].reason == "no_matching_value"
    turn = {
        "expected_capabilities": [{"capability": "aml.dossier", "order_index": 0}],
        "allowed_extra_capabilities": [],
        "forbidden_capabilities": [],
        "max_rounds": 3,
        "trajectory_match": "any_order",
        "min_precision": 0.8,
        "refusal_required": False,
    }
    traj = judge_turn(data, turn)
    assert not traj["passed"] and not traj["any_order"]


def test_a_record_maps_to_the_google_eval_case_shape() -> None:
    record = run_with_deadline(AlwaysAnswerStandin("42"), _request())
    case = to_agents_cli_case(record)
    assert case["prompt"]["parts"][0]["text"].startswith("What is the discrepancy")
    assert case["responses"][0]["response"]["parts"][0]["text"] == "42"
    events = case["agent_data"]["turns"][0]["events"]
    assert events[0]["author"] == "user" and events[-1]["content"]["parts"][0]["text"] == "42"
