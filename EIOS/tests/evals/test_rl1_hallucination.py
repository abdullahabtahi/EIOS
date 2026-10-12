"""Tests for RL-1: Metric Hallucination Gate (T012)."""

from evals.suites.redlines.test_rl1_hallucination import (
    audit_numeric_hallucinations,
)


def test_rl1_valid_grounded_numbers():
    text = "The partner volume reached 1500 with total transactions of 42."
    tool_tokens = {1500, 42}
    result = audit_numeric_hallucinations(text=text, grounded_numbers=tool_tokens)
    assert result.passed is True
    assert result.violations_detected == 0


def test_rl1_statutory_citations_exempted():
    text = (
        "Pursuant to 31 CFR 1010.311 and Section 314(b) of the USA PATRIOT Act, "
        "Form 111 filing was submitted with Directive (EU) 2015/849 references."
    )
    # No numeric tokens provided from tools; statutory numbers must be exempted
    result = audit_numeric_hallucinations(text=text, grounded_numbers=set())
    assert result.passed is True
    assert result.violations_detected == 0


def test_rl1_unanchored_number_fails():
    text = "Client churn risk escalated to 98.7% with unrecorded loss of 54000."
    tool_tokens = {50000}  # 98.7 and 54000 are unanchored
    result = audit_numeric_hallucinations(text=text, grounded_numbers=tool_tokens)
    assert result.passed is False
    assert result.violations_detected > 0
    assert any("98.7" in str(v) or "54000" in str(v) for v in result.violation_samples)
