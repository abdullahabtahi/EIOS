"""The conduct judge: a final answer never shows the model's working, never talks about its rules, and a refusal says
what can be done instead. Deterministic, over the turn record, so it is the same on a live run and a re-grade."""

from __future__ import annotations

from typing import Any

import pytest

from eios.agent_gates.core.conduct import judge_conduct


def _record(answer: str) -> dict[str, Any]:
    return {"answer": answer, "tool_calls": []}


@pytest.mark.parametrize(
    "answer",
    [
        "Wait, rule 7 says the briefing is not added.\nThe ring is causal.",
        "Let's check the dossier first. The ring is large.",
        "Per my instructions I cannot show that.",
    ],
)
def test_working_or_rule_talk_fails(answer: str) -> None:
    result = judge_conduct(_record(answer), {})
    assert not result["passed"] and result["reasons"]


def test_a_plain_answer_passes() -> None:
    assert judge_conduct(_record("The mule ring is causal: the refuter passed."), {})["passed"]


def test_a_refusal_with_a_next_step_passes() -> None:
    answer = "I cannot answer that because it is outside this workstation. I can answer questions about account risk."
    assert judge_conduct(_record(answer), {"refusal_required": True})["passed"]


def test_a_bare_refusal_fails() -> None:
    result = judge_conduct(
        _record("I cannot answer that because it is outside this workstation."), {}
    )
    assert not result["passed"]
    assert any("next step" in r for r in result["reasons"])


def test_a_bare_refusal_is_only_checked_when_it_opens_the_answer_or_one_is_required() -> None:
    assert judge_conduct(_record("The ring is large, and I cannot say more here."), {})["passed"]
    assert not judge_conduct(_record("No."), {"refusal_required": True})["passed"]


def test_required_mentions_are_checked_case_insensitively() -> None:
    turn = {"must_mention": ["payout", "Confounding"]}
    assert judge_conduct(_record("Run the Payout shock; a refuter cannot see confounding."), turn)[
        "passed"
    ]
    result = judge_conduct(_record("Run the payout shock."), turn)
    assert not result["passed"] and any("confounding" in r.lower() for r in result["reasons"])


def test_the_reasons_never_quote_the_answer() -> None:
    result = judge_conduct(_record("Wait, rule 7 says secret wording."), {})
    assert all("secret wording" not in r for r in result["reasons"])


@pytest.mark.parametrize(
    "answer",
    [
        "I cannot answer that because it asks about 2030. Here I can examine current partner risk signals.",
        "The data is not available because the spread edge failed. The shock with a tested path is competitor payout.",
        "The data is not available. You can run a simulation for a competitor payout increase instead.",
    ],
)
def test_the_next_step_is_recognised_in_the_ways_the_model_words_it(answer: str) -> None:
    assert judge_conduct(_record(answer), {"refusal_required": True})["passed"]


def test_the_platform_fail_closed_wording_counts_as_a_refusal_for_the_trajectory_judge() -> None:
    from eios.agent_gates.core.trajectory import REFUSAL

    assert REFUSAL.search(
        "I could not put together an answer I can fully support from the governed data."
    )


@pytest.mark.parametrize(
    "answer",
    [
        "I cannot run that simulation because the spread edge failed the causal gate.",
        "The competitor spread cut has no tested causal path to revenue because the spread edge failed.",
        "The data does not show it. The shock has no tested causal path to revenue.",
    ],
)
def test_the_ways_the_model_declines_an_untested_shock_count_as_a_refusal(answer: str) -> None:
    from eios.agent_gates.core.trajectory import REFUSAL

    assert REFUSAL.search(answer)
