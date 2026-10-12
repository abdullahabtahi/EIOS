"""Deterministic server-side AML and anti-fraud functions (US4)."""

from typing import Any

from eios.ontology.core.objects import ClientAccount


def ring_membership(
    members: list[str],
    shared_attrs: list[str],
    turnover_symmetry: float = 0.5,
) -> dict[str, Any]:
    """Calculate syndicate ring severity score based on clique topology and volume symmetry."""
    size_factor = min(1.0, len(members) / 3.0)
    attr_factor = min(1.0, len(shared_attrs) / 2.0)
    symmetry_factor = min(1.0, turnover_symmetry)

    score = 0.35 * size_factor + 0.35 * attr_factor + 0.30 * symmetry_factor
    score = round(min(1.0, max(0.0, score)), 3)

    return {
        "severity_score": score,
        "member_count": len(members),
        "shared_attribute_count": len(shared_attrs),
        "turnover_symmetry": turnover_symmetry,
        "is_actionable": score >= 0.75,
    }


def client_quality_score(
    client: ClientAccount,
    deposit_withdrawal_ratio: float = 1.0,
    chargeback_count: int = 0,
) -> float:
    """Calculate composite client quality score [0.0, 1.0]."""
    base_score = 0.55 if client.segment == "VIP" else 0.40
    tenure_bonus = min(0.20, client.lifetime_value_usd / 50000.0)
    flow_factor = min(0.25, deposit_withdrawal_ratio * 0.10)
    chargeback_penalty = chargeback_count * 0.35

    final_score = base_score + tenure_bonus + flow_factor - chargeback_penalty
    return round(min(1.0, max(0.0, final_score)), 3)
