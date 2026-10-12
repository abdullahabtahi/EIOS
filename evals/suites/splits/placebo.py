"""Placebo Causal Edge Refutation Verifier (T044).

Enforces Constitution Principle III and Anti-Circularity Benchmark Framework.
Planted placebo DAG edges (true effect = 0) must be tested against placebo-treatment refuters.
Pass condition: Placebo effect is indistinguishable from 0 (p > 0.05 on the placebo).
If p <= 0.05, a spurious causal effect has been falsely detected, failing the causal gate.
"""

from typing import Any


def verify_placebo_rejection(
    edge_id: str,
    true_effect: float,
    estimated_effect: float,
    refuter_p_value: float,
) -> dict[str, Any]:
    """Verify that a planted placebo edge passes refutation checks (p > 0.05).

    Args:
        edge_id: Identifier of evaluated causal edge in the DAG.
        true_effect: Ground-truth effect (0.0 for planted placebo edges).
        estimated_effect: Point estimate of treatment effect.
        refuter_p_value: p-value from placebo-treatment refutation test.

    Returns:
        Verification outcome dictionary including pass status and refuter metrics.
    """
    is_placebo = abs(true_effect) < 1e-6
    # For a placebo edge, a successful refuter shows effect is NOT statistically
    # distinguishable from 0 (p > 0.05)
    passed = refuter_p_value > 0.05 if is_placebo else True

    failure_reason = ""
    if not passed:
        failure_reason = (
            f"Placebo refuter failed on edge '{edge_id}': spurious effect {estimated_effect:.4f} "
            f"detected with p-value={refuter_p_value:.4f} <= 0.05 threshold."
        )

    return {
        "edge_id": edge_id,
        "is_placebo": is_placebo,
        "true_effect": true_effect,
        "estimated_effect": estimated_effect,
        "refuter_p_value": refuter_p_value,
        "passed": passed,
        "placebo_rejected": not passed,
        "failure_reason": failure_reason,
    }
