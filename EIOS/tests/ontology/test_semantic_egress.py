"""Tests for SemanticEgressGate safety inspection and sanitization (FM-5 Countermeasure)."""

from eios.ontology.omcp.semantic_egress import SemanticEgressGate


def test_defamatory_allegations_flagged_and_sanitized():
    gate = SemanticEgressGate()

    text = "The partner is a known fraudster involved in a criminal scheme and money launderer network."
    result = gate.inspect_and_sanitize(text)

    assert result.is_safe is False
    assert result.has_blocking_errors is True
    assert len(result.violations) == 3
    assert any("fraudster" in v.matched_term.lower() for v in result.violations)

    # Sanitized output should replace inflammatory allegations with objective compliance terms
    assert "fraudster" not in result.sanitized_text.lower()
    assert "party under anomaly review" in result.sanitized_text.lower()


def test_overconfident_certainty_adjusted_to_probabilistic_language():
    gate = SemanticEgressGate()

    text = "Partner P-402 is guaranteed to churn with zero chance of retention."
    result = gate.inspect_and_sanitize(text)

    # Warnings do not block egress if no severe errors exist
    assert result.is_safe is True
    assert len(result.violations) == 2
    assert any(v.severity == "WARNING" for v in result.violations)

    assert "guaranteed to churn" not in result.sanitized_text
    assert "projected high churn risk" in result.sanitized_text
    assert "low baseline retention probability" in result.sanitized_text


def test_strict_provenance_mode_flags_untagged_numbers():
    gate_strict = SemanticEgressGate(strict_provenance=True)

    text_untagged = "Retention revenue will drop by 45% ($250,000 loss) next month."
    result_fail = gate_strict.inspect_and_sanitize(text_untagged)
    assert result_fail.is_safe is False
    assert any(v.rule_id == "egress.unlabelled_numeric_claim" for v in result_fail.violations)

    text_tagged = (
        "Retention revenue will drop by 45% [ASSUMPTION] ($250,000 [TARGET] loss) next month."
    )
    result_ok = gate_strict.inspect_and_sanitize(text_tagged)
    assert result_ok.is_safe is True
    assert not any(v.rule_id == "egress.unlabelled_numeric_claim" for v in result_ok.violations)


def test_benign_executive_briefing_passes_cleanly():
    gate = SemanticEgressGate()

    text = "Partner P-102 exhibits an elevated churn risk probability of 78.4% due to rebate compression."
    result = gate.inspect_and_sanitize(text)

    assert result.is_safe is True
    assert len(result.violations) == 0
    assert result.sanitized_text == text
