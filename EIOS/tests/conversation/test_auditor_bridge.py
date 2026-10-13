"""Tests for Metric Auditor Gate bridge with legal citation normalization (F018, T005)."""

import pytest

from eios.conversation.auditor_bridge import ConversationAuditorBridge
from eios.ontology.auditor.gate import MetricAuditorGate


@pytest.fixture
def bridge():
    auditor = MetricAuditorGate(relative_tolerance=0.01)
    return ConversationAuditorBridge(auditor)


def test_auditor_bridge_passes_anchored_tool_metrics(bridge):
    tool_trace = [
        {
            "tool": "inspect_aml_entity",
            "output": {
                "entity_id": "CR84920",
                "discrepancy_multiplier": 16.0,
                "net_deposit_volume_30d_usd": 8000.0,
            },
        }
    ]
    narrative = (
        "Entity CR84920 observed with a 16.0x discrepancy multiplier and $8,000 in turnover."
    )
    record = bridge.audit_turn(narrative, tool_trace, trace_id="tr_valid")
    assert record.passed is True
    assert record.status.value == "PASS"


def test_auditor_bridge_exempts_statutory_and_legal_citations(bridge):
    """Statutory citations must not trigger false-positive numerical hallucination blocks."""
    tool_trace = [
        {
            "tool": "inspect_aml_entity",
            "output": {
                "discrepancy_multiplier": 16.0,
            },
        }
    ]
    narrative = (
        "Under 31 CFR § 1020.320 and Section 314(b), the 16.0x discrepancy multiplier "
        "warrants filing FinCEN Form 111."
    )
    record = bridge.audit_turn(narrative, tool_trace, trace_id="tr_legal")
    assert record.passed is True
    assert record.status.value == "PASS"
    assert any(
        "1020.320" in c or "111" in c or "314" in c for c in record.exempted_statutory_citations
    )


REVENUE_TRACE = [{"tool": "get_governed_metric", "output": {"net_revenue_usd": 3820000.0}}]


@pytest.mark.parametrize(
    "narrative",
    [
        "Revenue was USD9999999 last month.",  # currency prefix glued to the figure
        "Net revenue reached x500 units across brokers.",  # letter-prefixed 3-digit figure
        "Churn loss was estimated at EUR50 per partner.",  # currency code, short digit run
        "Exposure hit CR99999999 in total.",  # id-shaped token no tool or query produced
    ],
)
def test_identifier_exemption_cannot_launder_a_metric(bridge, narrative):
    """Letters-then-digits must not be a free pass: an ungrounded token's digits are still audited."""
    record = bridge.audit_turn(narrative, REVENUE_TRACE, trace_id="tr_laundering")
    assert record.passed is False, narrative
    assert record.status.value == "BLOCKED"


def test_identifier_grounded_in_tool_output_is_exempt(bridge):
    trace = [
        {
            "tool": "inspect_aml_entity",
            "output": {"entity_id": "CR84920", "discrepancy_multiplier": 16.0},
        }
    ]
    record = bridge.audit_turn("CR84920 shows a 16.0x discrepancy multiplier.", trace)
    assert record.passed is True


def test_identifier_grounded_in_operator_query_is_exempt(bridge):
    record = bridge.audit_turn(
        "Partner AP1029 has the highest hazard.",
        REVENUE_TRACE,
        query="What is AP1029's churn hazard?",
    )
    assert record.passed is True


@pytest.mark.parametrize(
    "narrative", ["Q3 policy review applies.", "The Tier1 playbook is active.", "Phase P1 is open."]
)
def test_short_structural_codes_stay_exempt(bridge, narrative):
    assert bridge.audit_turn(narrative, REVENUE_TRACE).passed is True


def test_identifier_masking_does_not_corrupt_overlapping_tokens(bridge):
    """One token being a substring of another must not leak digits through a partial replace."""
    trace = [{"tool": "t", "output": {"entity_id": "CR84920"}}]
    record = bridge.audit_turn("CR84920 and R849201 were both reviewed.", trace)
    assert record.passed is False  # R849201 is ungrounded and long; its digits must be audited


def test_auditor_bridge_blocks_unanchored_kpi_metrics(bridge):
    tool_trace = [
        {
            "tool": "get_governed_metric",
            "output": {"net_revenue_usd": 3820000.0},
        }
    ]
    # Fabricated metric: $950,000 not in tool trace
    narrative = "Net revenue was $3,820,000 while churn loss was estimated at $950,000."
    record = bridge.audit_turn(narrative, tool_trace, trace_id="tr_hallucinated")
    assert record.passed is False
    assert record.status.value == "BLOCKED"
    assert len(record.unanchored_tokens) > 0
