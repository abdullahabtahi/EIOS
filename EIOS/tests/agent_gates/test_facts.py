"""Fact flattening tests (T016): every numeric leaf of a tool result becomes a labelled fact."""

import pytest

from eios.agent_gates.core.facts import flatten_facts


def _calls(result: dict[str, object], name: str = "tool") -> list[dict[str, object]]:
    return [{"name": name, "arguments": {}, "result": result}]


def _by_path(facts, suffix: str):  # type: ignore[no-untyped-def]
    (match,) = [f for f in facts if f.path.endswith(suffix)]
    return match


def test_nested_results_and_lists_are_flattened() -> None:
    facts = flatten_facts(
        _calls({"deltas": {"net_revenue_delta_usd": -1_107_800.0}, "ci": [1.0, 2.0]})
    )
    assert _by_path(facts, "deltas.net_revenue_delta_usd").value == -1_107_800.0
    assert {f.path for f in facts} >= {"0.ci[0]", "0.ci[1]"}


def test_booleans_and_strings_are_not_facts() -> None:
    facts = flatten_facts(_calls({"passed": True, "name": "x", "n": 3}))
    assert [f.path for f in facts] == ["0.n"]


@pytest.mark.parametrize(
    ("key", "unit"),
    [
        ("net_revenue_usd", "currency"),
        ("churn_hazard_probability", "ratio"),
        ("decay_pct", "percent"),
        ("spread_bps", "bps"),
        ("discrepancy_multiplier", "multiplier"),
        ("sla_hours", "duration"),
        ("velocity_transfers_count", "count"),
        ("composite_risk_score", "other"),
    ],
)
def test_unit_family_is_inferred_from_the_field_name(key: str, unit: str) -> None:
    (fact,) = flatten_facts(_calls({key: 5.0}))
    assert fact.unit == unit


def test_a_sibling_unit_field_wins_over_the_name() -> None:
    (fact,) = flatten_facts(
        _calls({"metric_id": "net_revenue", "value": 3_820_000.0, "unit": "USD"})
    )
    assert fact.unit == "currency"


def test_label_tokens_come_from_the_path_and_sibling_metric_names() -> None:
    (fact,) = flatten_facts(_calls({"metric_id": "net_revenue_usd", "value": 3_820_000.0}))
    assert {"net", "revenue"} <= set(fact.label_tokens)
    assert "usd" not in fact.label_tokens


def test_period_and_window_are_read_from_the_name() -> None:
    (monthly,) = flatten_facts(_calls({"kyc_declared_monthly_income_usd": 500.0}))
    assert monthly.period == "month"
    (windowed,) = flatten_facts(_calls({"decay_percentage_14d": 62.4}))
    assert 14 in windowed.windows


def test_aliases_add_label_words_for_a_field() -> None:
    plain = flatten_facts(_calls({"discrepancy_multiplier": 16.0}))[0]
    aliased = flatten_facts(
        _calls({"discrepancy_multiplier": 16.0}),
        {"discrepancy_multiplier": ["times declared income"]},
    )[0]
    assert "declared" not in plain.label_tokens
    assert "declared" in aliased.label_tokens


def test_calls_with_errors_contribute_no_facts() -> None:
    calls: list[dict[str, object]] = [
        {"name": "t", "arguments": {}, "result": None, "error": "NOT_FOUND"}
    ]
    assert flatten_facts(calls) == []
