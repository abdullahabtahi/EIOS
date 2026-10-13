"""Numeric-faithfulness eval cases for the Metric Auditor, including its measured gaps (docs/adk.md section 3).

The auditor checks "does this digit string appear anywhere in the tool output", with a x100 scale
tolerance. It has no link between a claim and the field it came from. The cases below were measured on
2026-10-13 against the repo's own fixture tool results.

- `PASSING_TODAY` must keep passing through the migration to ADK.
- `KNOWN_FALSE_PASSES` and `KNOWN_FALSE_POSITIVES` are strict expected failures: when the replacement
  design (reference-based rendering, adk.md section 3) fixes one, the strict xfail turns into an error,
  which forces the marker to be removed so the case becomes a normal regression test.
"""

import pytest

from eios.conversation.auditor_bridge import ConversationAuditorBridge
from eios.conversation.tools import get_governed_metric, inspect_aml_entity, run_causal_what_if

QUERY = "Check CR84920 and net revenue"


@pytest.fixture(scope="module")
def trace() -> list[dict[str, object]]:
    return [
        {"tool": "inspect_aml_entity", "output": inspect_aml_entity("CR84920")},
        {"tool": "get_governed_metric", "output": get_governed_metric("net_revenue_usd")},
        {
            "tool": "run_causal_what_if",
            "output": run_causal_what_if("competitor_spread_delta_bps", 20.0),
        },
    ]


def _passes(text: str, trace: list[dict[str, object]]) -> bool:
    return ConversationAuditorBridge().audit_turn(text, trace, query=QUERY).passed


PASSING_TODAY = {
    "multiplier": ("CR84920 shows a 16.0x discrepancy multiplier.", True),
    "revenue": ("Net revenue is $3,820,000 USD.", True),
    "date_and_count": ("As of 2026-10-13 the ring has 23 accounts.", True),
    "invented_ring_size": ("The ring has 47 members.", False),
    "invented_rounded_revenue": ("Revenue is $3.9 million.", False),
    "unanchored_derived_percent": ("Deposits were 16 times income, i.e. 1,500% higher.", False),
}

# Answers that are wrong but pass: no claim-to-field binding, x100 tolerance, spelled-out numbers, units.
KNOWN_FALSE_PASSES = {
    "wrong_field": "The composite risk score of CR84920 is 16.",
    "hundred_times_too_small": "Net revenue is $38,200 USD.",
    "hundred_times_too_large": "The velocity is 1600 transfers.",
    "spelled_out_numbers": "Net revenue is about three million dollars and sixteen accounts are linked.",
    "wrong_unit": "Declared income was $500 per week.",
}

# Correct answers that are blocked: no support for scaled shorthand or harmless list counts.
KNOWN_FALSE_POSITIVES = {
    "million_shorthand": "Revenue is about $3.8 million.",
    "harmless_counts": "There are 3 key findings across 2 sources.",
}


@pytest.mark.parametrize(("text", "expected"), PASSING_TODAY.values(), ids=PASSING_TODAY.keys())
def test_current_behaviour_that_must_survive_the_migration(
    trace: list[dict[str, object]], text: str, expected: bool
) -> None:
    assert _passes(text, trace) is expected


@pytest.mark.xfail(strict=True, reason="auditor has no claim-to-field binding (adk.md section 3)")
@pytest.mark.parametrize("text", KNOWN_FALSE_PASSES.values(), ids=KNOWN_FALSE_PASSES.keys())
def test_a_wrong_figure_must_be_blocked(trace: list[dict[str, object]], text: str) -> None:
    assert _passes(text, trace) is False


@pytest.mark.xfail(strict=True, reason="auditor does not parse scaled shorthand or list counts")
@pytest.mark.parametrize("text", KNOWN_FALSE_POSITIVES.values(), ids=KNOWN_FALSE_POSITIVES.keys())
def test_a_faithful_answer_must_not_be_blocked(trace: list[dict[str, object]], text: str) -> None:
    assert _passes(text, trace) is True
