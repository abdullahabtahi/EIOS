"""Red-Line Test RL-1: Metric Auditor Gate numeric provenance firewall (T033)."""

from eios.ontology.auditor.gate import AuditVerificationRecord, MetricAuditorGate


def test_auditor_gate_passes_compliant_response(sample_tool_trace):
    gate = MetricAuditorGate(relative_tolerance=0.01)
    text = "Partner 8821 generated $142,500 in net deposits across 38 first-time deposits."

    record = gate.audit(narrative_text=text, tool_trace=sample_tool_trace)

    assert isinstance(record, AuditVerificationRecord)
    assert record.audit_passed is True
    assert len(record.untraceable_numbers) == 0
    assert 142500.0 in record.anchored_numbers
    assert 38.0 in record.anchored_numbers


def test_auditor_gate_blocks_hallucinated_number(sample_tool_trace):
    gate = MetricAuditorGate(relative_tolerance=0.01)
    # The trace contains 142500.0 and 38.0, but NOT 49.5% or $99,000
    text = "Partner generated $99,000 with a churn hazard of 49.5%."

    record = gate.audit(narrative_text=text, tool_trace=sample_tool_trace)

    assert record.audit_passed is False
    assert len(record.untraceable_numbers) >= 1
    assert any("99,000" in s or "99000" in s for s in record.untraceable_numbers)


def test_auditor_gate_permits_honest_uncertainty(sample_tool_trace):
    gate = MetricAuditorGate()
    text = "There is insufficient data available to calculate the 90-day churn hazard."

    record = gate.audit(narrative_text=text, tool_trace=sample_tool_trace)

    assert record.audit_passed is True
    assert len(record.extracted_numbers) == 0


def test_auditor_gate_relative_tolerance_allows_minor_rounding(sample_tool_trace):
    gate = MetricAuditorGate(relative_tolerance=0.01)
    # Trace churn hazard is 0.28. Agent states "28.1%" (within 1% relative tolerance)
    text = "The partner exhibits a 28.1% churn hazard score."

    record = gate.audit(narrative_text=text, tool_trace=sample_tool_trace)
    assert record.audit_passed is True
