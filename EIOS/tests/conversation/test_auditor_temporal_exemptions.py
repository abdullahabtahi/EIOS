"""Dates, timestamps and version labels are not business metrics; wrong business figures are still blocked (RL-1)."""

import pytest

from eios.conversation.auditor_bridge import ConversationAuditorBridge

TRACE = [
    {
        "tool": "get_governed_metric",
        "output": {"metric_id": "net_revenue_usd", "value": 3820000.0, "unit": "USD"},
    }
]


@pytest.fixture
def audit():
    bridge = ConversationAuditorBridge()
    return lambda text: bridge.audit_turn(text, TRACE)


@pytest.mark.parametrize(
    "text",
    [
        "Net revenue is $3,820,000 USD as of 2026-10-13 10:19:14 UTC.",
        "Net revenue is $3,820,000 (definition v1.4.0).",
        "As of 2026-10-13T10:19:14Z the figure is $3,820,000.",
        "Per version 2.1.3 of the registry, net revenue is $3,820,000.",
        "Net revenue was $3,820,000 on 2026-10-13.",
    ],
)
def test_correct_figure_with_dates_and_versions_passes(audit, text):
    result = audit(text)
    assert result.passed, result.unanchored_tokens


@pytest.mark.parametrize(
    "text",
    [
        "Net revenue is $3,900,000 as of 2026-10-13 10:19:14 UTC.",
        "Net revenue is $3,900,000 (definition v1.4.0).",
        "On 2026-10-13 net revenue reached $5,000,000.",
        "The 3:20 ratio of revenue to cost is 3820000 and growth is 14%.",
    ],
)
def test_wrong_or_unanchored_figures_are_still_blocked(audit, text):
    assert not audit(text).passed


def test_a_bare_decimal_is_not_mistaken_for_a_version(audit):
    assert not audit("Margin is 2.5 and revenue is $3,820,000.").passed
