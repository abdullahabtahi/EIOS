"""Mutation and paraphrase corpora (T018): every wrong variant is caught, no faithful variant is blocked.

A figure is either right or wrong; the judge has to tell scale, field, unit, period and precision errors
apart from legitimate rewordings. Measured precision and recall go in research.md R-2.
"""

from typing import Any

import pytest

from eios.agent_gates.core.faithfulness import judge

RESULT = {
    "entity_id": "CR84920",
    "composite_risk_score": 89,
    "kyc_declared_monthly_income_usd": 500.0,
    "net_deposit_volume_30d_usd": 8000.0,
    "discrepancy_multiplier": 16.0,
    "syndicate_ring_size": 23,
    "velocity_transfers_count": 16,
    "churn_hazard_probability": 0.78,
    "login_decay_pct": -68.0,
    "sla_hours": 4.8,
    "net_revenue_usd": 3_820_000.0,
}

FAITHFUL = [
    "Net revenue is $3,820,000.",
    "Net revenue is $3.82 million.",
    "Net revenue is about $3.8 million.",
    "Net revenue is 3.82M USD.",
    "The discrepancy multiplier is 16.0x.",
    "The discrepancy multiplier is 16 times.",
    "The syndicate ring size is 23.",
    "The ring has twenty-three accounts.",
    "The churn hazard probability is 0.78.",
    "The churn hazard is 78%.",
    "Login decay is -68%.",
    "Login activity has dropped 68%.",
    "The SLA is 4.8 hours.",
    "Velocity is 16 transfers.",
    "Declared monthly income is $500.",
    "Declared income is $500 per month.",
    "Net deposit volume over 30 days is $8,000.",
    "The composite risk score is 89.",
    "CR84920 has a composite risk score of 89.",
    "Net revenue is $3,820,000 and the ring size is 23.",
]

WRONG = {
    "scale_x100_revenue": "Net revenue is $382,000,000.",
    "scale_x100_multiplier": "The discrepancy multiplier is 1600x.",
    "scale_x100_ring": "The syndicate ring size is 2300.",
    "scale_x100_velocity": "Velocity is 1,600 transfers.",
    "scale_div100_revenue": "Net revenue is $38,200.",
    "scale_div100_score": "The composite risk score is 0.89.",
    "field_swap_score": "The composite risk score is 16.",
    "field_swap_ring": "The syndicate ring size is 16.",
    "field_swap_income": "Declared income is $8,000.",
    "field_swap_multiplier": "The discrepancy multiplier is 89x.",
    "unit_swap_percent": "Net revenue is 3,820,000%.",
    "unit_swap_currency": "The churn hazard is $78.",
    "unit_swap_duration": "The SLA is 4.8 days.",
    "dropped_decimal_duration": "The SLA is 48 hours.",
    "dropped_decimal_revenue": "Net revenue is $38.2 million.",
    "dropped_decimal_hazard": "The churn hazard is 7.8%.",
    "derived_percent": "Deposits are 1,500% higher than declared income.",
    "derived_growth": "Net revenue grew 40% last quarter.",
    "period_swap": "Declared income is $500 per week.",
    "invented": "The ring has 47 members.",
    "rounded_wrong": "Net revenue is about $3.9 million.",
    "spelled_wrong": "Net revenue is about three million dollars.",
    "ungrounded_id": "CR99999 has a composite risk score of 89.",
}


def _record(answer: str) -> dict[str, Any]:
    return {
        "answer": answer,
        "question": "Check CR84920",
        "entity_context": {"entity_id": "CR84920"},
        "tool_calls": [
            {"name": "inspect_aml_entity", "arguments": {"entity_id": "CR84920"}, "result": RESULT}
        ],
    }


@pytest.mark.parametrize("answer", FAITHFUL)
def test_no_faithful_paraphrase_is_blocked(answer: str) -> None:
    result = judge(_record(answer))
    assert result.passed, [
        (v.text, v.reason) for v in result.verdicts if v.verdict == "unsupported"
    ]


@pytest.mark.parametrize(("name", "answer"), list(WRONG.items()), ids=list(WRONG))
def test_every_mutant_is_caught(name: str, answer: str) -> None:
    assert not judge(_record(answer)).passed, name


def test_corpus_sizes_are_what_the_report_claims() -> None:
    assert (len(FAITHFUL), len(WRONG)) == (20, 23)
