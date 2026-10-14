"""Bugs the held-out corpus (T025) found in the judge, kept as permanent cases.

Each was a real disagreement between the judge and the corpus's known answer before it was fixed.
"""

from typing import Any

import pytest

from eios.agent_gates.core.faithfulness import judge


def _rec(answer: str, result: dict[str, Any], aliases: dict[str, list[str]] | None = None) -> Any:
    record = {
        "answer": answer,
        "question": "q",
        "entity_context": None,
        "tool_calls": [{"name": "t", "arguments": {}, "result": result}],
    }
    return judge(record, aliases)


LEDGER = {"entries_count": 1842, "head_sequence": 1842, "chain_length": 1842}
OPS = {"dlq_depth": 3, "ingest_p95_ms": 142.0}
EXEC = {
    "metric_id": "net_revenue_usd",
    "value": 3_820_000.0,
    "unit": "USD",
    "forecast": {"net_revenue_forecast_usd": 4_050_000.0},
    "deltas": {"net_revenue_delta_usd": -1_107_800.0, "net_revenue_delta_percentage": -29.0},
}


@pytest.mark.parametrize(
    ("answer", "result", "aliases"),
    [
        # Two figures in one sentence must not borrow each other's labels.
        ("The ledger entries is 1,842 and the head sequence is 1,842.", LEDGER, None),
        # A statistic's name (p95) is not an invented identifier.
        ("The dead letter queue depth is 3 and the ingest p95 latency is 142.", OPS, None),
        # A minus sign before the currency symbol still means negative.
        ("Net revenue delta came to -$1,107,800.", EXEC, None),
        # A top-level unit hint must not leak into nested fields with their own unit.
        ("We see -29% for the net revenue delta.", EXEC, None),
        ("The net revenue forecast is $4,050,000.", EXEC, None),
        ("Net revenue is $3,820,000.", EXEC, None),
        # A synonym the field name lacks is supplied by the case, as golden cases do.
        (
            "First deposits are down 45%.",
            {"ftd_decay_pct": -45.0},
            {"ftd_decay_pct": ["first deposits"]},
        ),
        # Found by the first live run: the model writes "Label: `value`" bullets, so the label sits
        # before the colon. Without it every figure looked unlabelled and was marked wrong_field.
        (
            "* **Composite Risk Score**: `89`\n* **Syndicate Ring Size**: `23`\n"
            "* **Velocity Transfers Count**: `16`\n* **Discrepancy Multiplier**: `16`",
            {
                "composite_risk_score": 89,
                "syndicate_ring_size": 23,
                "velocity_transfers_count": 16,
                "discrepancy_multiplier": 16.0,
            },
            None,
        ),
    ],
)
def test_faithful_variants_the_corpus_found_are_accepted(
    answer: str, result: dict[str, Any], aliases: dict[str, list[str]] | None
) -> None:
    verdict = _rec(answer, result, aliases)
    assert verdict.passed, [(v.text, v.reason) for v in verdict.unsupported()]


@pytest.mark.parametrize(
    ("answer", "result", "reason"),
    [
        # The forecast value attached to the current-revenue words, and the reverse.
        ("The net revenue is $4,050,000.", EXEC, "ambiguous"),
        ("The net revenue forecast is $3,820,000.", EXEC, "ambiguous"),
        # An unknown synonym is refused (fail closed) until an alias says otherwise.
        ("First deposits are down 45%.", {"ftd_decay_pct": -45.0}, "wrong_field"),
    ],
)
def test_wrong_variants_the_corpus_found_are_blocked(
    answer: str, result: dict[str, Any], reason: str
) -> None:
    verdict = _rec(answer, result)
    assert not verdict.passed
    assert reason in {v.reason for v in verdict.unsupported()}


def test_a_figure_after_a_tool_failure_is_blocked() -> None:
    record: dict[str, Any] = {
        "answer": "The composite risk score is 89.",
        "question": "q",
        "entity_context": None,
        "tool_calls": [{"name": "t", "arguments": {}, "result": None, "error": "DATA_UNAVAILABLE"}],
    }
    assert not judge(record).passed


def test_a_long_sentence_naming_several_fields_is_not_ambiguous_when_each_figure_is_claimed() -> (
    None
):
    result = {
        "composite_risk_score": 89,
        "discrepancy_multiplier": 16.0,
        "kyc_declared_monthly_income_usd": 500.0,
        "net_deposit_volume_30d_usd": 8000.0,
        "velocity_transfers_count": 16,
    }
    answer = (
        "CR84920 presents a composite risk score of 89 with a 16.0x discrepancy multiplier between declared "
        "monthly income ($500 USD) and realized deposit turnover ($8,000 USD) across 16 transfers."
    )
    record = {
        "answer": answer,
        "question": "Check CR84920",
        "entity_context": None,
        "tool_calls": [{"name": "t", "arguments": {"entity_id": "CR84920"}, "result": result}],
    }
    verdict = judge(record)
    assert verdict.passed, [(v.text, v.reason) for v in verdict.unsupported()]


def test_a_window_named_in_a_metric_id_supports_a_thirty_day_figure() -> None:
    result = {"metric_id": "net_deposit_volume_30d_usd", "value": 482000.0, "unit": "USD"}
    verdict = _rec("Net deposit volume over the 30-day window was $482,000.", result)
    assert verdict.passed, [(v.text, v.reason) for v in verdict.unsupported()]
