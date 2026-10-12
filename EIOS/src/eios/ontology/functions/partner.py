"""Deterministic server-side partner analytics functions (US4)."""

from typing import Any

from eios.ontology.core.objects import Partner


def partner_value_at_risk(partner: Partner, hazard_score: float | None = None) -> float:
    """Calculate expected 30-day commission loss weighted by disengagement hazard."""
    effective_hazard = hazard_score if hazard_score is not None else partner.hazard_probability_30d
    if effective_hazard <= 0.0:
        effective_hazard = 0.20
    return round(float(partner.value_at_risk_usd) * float(effective_hazard), 2)


def churn_priority(partner: Partner, disengage_prob: float | None = None) -> dict[str, Any]:
    """Calculate composite partner retention priority based on hazard and Value-at-Risk."""
    prob = disengage_prob if disengage_prob is not None else partner.hazard_probability_30d
    if prob <= 0.0:
        prob = 0.25

    priority_score = round(float(partner.value_at_risk_usd) * float(prob), 2)

    # Risk tier determination
    if prob >= 0.50:
        risk_tier = "HIGH"
    elif prob >= 0.25:
        risk_tier = "MEDIUM"
    else:
        risk_tier = "LOW"

    # Intervention window timing
    if prob > 0.75:
        window = "LATE_STAGE"
    elif prob >= 0.35:
        window = "OPTIMAL"
    elif prob >= 0.20:
        window = "EARLY_WATCH"
    else:
        window = "STABLE"

    priority_tier = "CRITICAL" if prob >= 0.75 else ("HIGH" if prob >= 0.50 else "NORMAL")

    return {
        "partner_id": partner.partner_id,
        "score": round(prob, 3),
        "priority_score": priority_score,
        "risk_tier": risk_tier,
        "priority_tier": priority_tier,
        "intervention_window": window,
        "hazard_probability_30d": prob,
        "value_at_risk_usd": partner.value_at_risk_usd,
        "tier": partner.tier,
    }
