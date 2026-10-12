"""Tests for Placebo Causal Edge Rejection Verifier (T041)."""

from evals.suites.splits.placebo import verify_placebo_rejection


def test_planted_placebo_edge_passes_refuter():
    # A true placebo has true_effect = 0.0.
    # Refuter tests the null: effect == 0. A high p-value (p > 0.05) indicates effect is
    # indistinguishable from 0.
    # The refuter check PASSES if p > 0.05.
    res = verify_placebo_rejection(
        edge_id="placebo_campaign_to_dispute",
        true_effect=0.0,
        estimated_effect=0.001,
        refuter_p_value=0.72,
    )
    assert res["passed"] is True
    assert res["placebo_rejected"] is False  # Refuter confirmed no spurious effect
    assert res["refuter_p_value"] > 0.05


def test_spurious_placebo_edge_fails_causal_gate():
    # If a placebo edge shows a statistically significant effect (p <= 0.05),
    # it fails the causal gate
    res = verify_placebo_rejection(
        edge_id="spurious_noise_edge",
        true_effect=0.0,
        estimated_effect=0.35,
        refuter_p_value=0.01,  # p <= 0.05 -> refuter fails!
    )
    assert res["passed"] is False
    assert "refuter failed" in res["failure_reason"].lower()
