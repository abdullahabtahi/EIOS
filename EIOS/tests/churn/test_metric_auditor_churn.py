"""Tests verifying that Churn Radar explanation narratives pass MetricAuditorGate with 0 hallucinations (T015)."""

from eios.churn.models import RiskTier
from eios.churn.narrative import ChurnNarrativeGenerator
from eios.ontology.auditor.gate import MetricAuditorGate


def test_audited_narrative_passes_gate():
    """Verify that generated narrative strictly cites tool outputs and passes MetricAuditorGate."""
    generator = ChurnNarrativeGenerator()
    auditor = MetricAuditorGate()

    tool_output = {
        "partner_id": "P-CHURN-DRIFT",
        "hazard_probability_30d": 0.76,
        "priority_score": 34200.0,
        "value_at_risk_usd": 45000.0,
        "decay_pct": 42.0,
        "risk_tier": "HIGH",
    }

    narrative = generator.generate_narrative(
        partner_id=tool_output["partner_id"],
        risk_tier=RiskTier.HIGH,
        hazard_prob=tool_output["hazard_probability_30d"],
        value_at_risk=tool_output["value_at_risk_usd"],
        top_family="BEHAVIORAL",
        top_driver_metric="login decay",
        top_driver_delta=tool_output["decay_pct"],
        citations=["DP6:partner_360", "DP9:partner_engagement_signals"],
    )

    tool_trace = [{"tool_name": "get_partner_signals", "output": tool_output}]

    audit_result = auditor.verify_response(narrative.narrative, tool_trace)
    assert audit_result.passed is True, (
        f"Auditor rejected narrative: {audit_result.untraced_tokens}"
    )
    assert len(narrative.citations) >= 2


def test_audited_narrative_blocks_hallucination():
    """Verify that hallucinated figures injected into narrative are detected and blocked."""
    auditor = MetricAuditorGate()

    tool_output = {
        "partner_id": "P-CHURN-DRIFT",
        "hazard_probability_30d": 0.76,
        "value_at_risk_usd": 45000.0,
    }

    # Injected hallucinated metric: 99.5%
    hallucinated_text = "Partner P-CHURN-DRIFT has a 99.5% chance of defecting to competitor."
    tool_trace = [{"tool_name": "get_partner_signals", "output": tool_output}]

    audit_result = auditor.verify_response(hallucinated_text, tool_trace)
    assert audit_result.passed is False
    assert any("99.5" in token for token in audit_result.untraceable_numbers)
