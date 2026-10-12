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
    narrative = "Entity CR84920 observed with a 16.0x discrepancy multiplier and $8,000 in turnover."
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
    assert any("1020.320" in c or "111" in c or "314" in c for c in record.exempted_statutory_citations)


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
