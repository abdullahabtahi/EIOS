"""Tests for RL-5: PII Leakage Scanner (T016)."""

from evals.suites.redlines.test_rl5_pii_leakage import (
    scan_text_for_pii,
)


def test_rl5_pseudonymized_text_passes():
    text = (
        "User tok_usr_902bf within cluster tok_id_cluster_e310 traded 400 shares "
        "linked to synthetic entity ent_syn_19."
    )
    result = scan_text_for_pii(text)
    assert result.passed is True
    assert result.violations_detected == 0


def test_rl5_raw_email_fails():
    text = "Please reach out to alice.smith@corporate-bank.com regarding account status."
    result = scan_text_for_pii(text)
    assert result.passed is False
    assert result.violations_detected > 0
    assert any("email" in str(v).lower() for v in result.violation_samples)


def test_rl5_raw_credit_card_and_ssn_fails():
    text = "Card 4532-8921-9982-1234 was billed; SSN on file is 123-45-6789."
    result = scan_text_for_pii(text)
    assert result.passed is False
    assert result.violations_detected >= 2
