"""Tests for RL-2: Citation & Provenance Coverage Gate (T013)."""

from evals.suites.redlines.test_rl2_citation import (
    verify_citation_coverage,
)


def test_rl2_valid_citations():
    text = (
        "Client tok_usr_8829a exhibited anomalous outbound spikes under P-102 "
        "with metric as_of 2026-10-01T12:00:00Z and definition_version v1.2.0."
    )
    result = verify_citation_coverage(text)
    assert result.passed is True
    assert result.violations_detected == 0


def test_rl2_missing_citation_fails():
    text = "The user has performed multiple suspicious transactions recently."
    result = verify_citation_coverage(text)
    assert result.passed is False
    assert result.violations_detected > 0
    assert "Missing required entity or timestamp citations" in str(result.violation_samples)
