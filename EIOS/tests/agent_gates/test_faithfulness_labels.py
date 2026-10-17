"""A name a tool returned is a name, not a figure: the judge flagged digits inside labels the model copied verbatim.

Found by the live baseline of 2026-10-17: eight of its nine failures were these false positives (a product called
"Boom 1000", a gateway "PA-HUB-007", red lines named "p > 0.05" and "Zero LLM Metric Calculation", the shorthand
"30d"). A label is exempt only when a tool returned it verbatim and it is short and carries no percent or currency
sign, so a number typed into a sentence is still judged.
"""

from __future__ import annotations

from typing import Any

import pytest

from eios.agent_gates.core.faithfulness import judge


def _judged(answer: str, result: dict[str, Any]) -> Any:
    record = {
        "answer": answer,
        "question": "q",
        "entity_context": None,
        "tool_calls": [{"name": "t", "arguments": {}, "result": result}],
    }
    return judge(record)


@pytest.mark.parametrize(
    ("answer", "result"),
    [
        (
            "The scheme runs on Boom 1000 with paired accounts.",
            {"products": [{"name": "Boom 1000"}]},
        ),
        (
            "Central Payment Gateway #007 (PA-HUB-007) is shared.",
            {"gateways": [{"label": "Central Payment Gateway #007", "gateway_id": "PA-HUB-007"}]},
        ),
        (
            "Refuter Placebo Threshold p > 0.05: PASS. Zero LLM Metric Calculation: PASS.",
            {
                "red_lines": [
                    {"name": "Refuter Placebo Threshold p > 0.05", "status": "PASS"},
                    {"name": "Zero LLM Metric Calculation", "status": "PASS"},
                ]
            },
        ),
    ],
)
def test_a_label_copied_verbatim_from_a_tool_result_is_not_a_figure(
    answer: str, result: dict[str, Any]
) -> None:
    assert _judged(answer, result).passed


def test_the_same_digits_with_no_such_label_in_a_result_are_still_judged() -> None:
    assert not _judged(
        "The scheme runs on Boom 1000.", {"products": [{"name": "Crash 500"}]}
    ).passed


def test_a_sentence_with_figures_is_not_a_label_even_when_copied_verbatim() -> None:
    sentence = "breach rate 0.390% against a budget of 0.050%"
    assert not _judged(sentence, {"alerts": [{"message": sentence}]}).passed


def test_a_label_that_carries_a_currency_or_percent_sign_is_not_exempt() -> None:
    assert not _judged("The tier is Gold 5%.", {"tiers": [{"name": "Gold 5%"}]}).passed


def test_a_thirty_day_shorthand_is_the_window_a_field_name_states() -> None:
    result = {"realized_volume_30d_usd": 236240.0, "units": {"realized_volume_30d_usd": "USD"}}
    assert _judged("Realized 30d volume is $236.24K.", result).passed
