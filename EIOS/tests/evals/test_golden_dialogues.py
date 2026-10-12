"""Tests for Golden Dialogue Scenario Loader (T046)."""

from pathlib import Path

from evals.golden.trajectory_eval import (
    load_all_golden_dialogues,
    load_golden_dialogue,
)


def test_load_all_ten_golden_dialogues():
    dialogues_dir = Path("evals/golden/dialogues")
    scenarios = load_all_golden_dialogues(dialogues_dir)
    assert len(scenarios) >= 10

    for sc in scenarios:
        assert sc.scenario_id
        assert sc.domain
        assert len(sc.turns) >= 1
        for turn in sc.turns:
            assert turn.user_query
            assert turn.expected_route


def test_unanswerable_query_requires_refusal():
    dialogues_dir = Path("evals/golden/dialogues")
    scenario = load_golden_dialogue(dialogues_dir / "unanswerable_query.yaml")
    assert any(turn.refusal_required for turn in scenario.turns)
