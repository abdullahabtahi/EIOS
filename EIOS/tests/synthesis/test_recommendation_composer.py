"""Tests for Governed Recommendation Composer and Action Intent emission (T027, US5)."""

from eios.ontology.actions.intent_hub import ActionIntentHub, ActionIntentToken, ActionStatus
from eios.synthesis.models import RecommendationCard
from eios.synthesis.recommendations import RecommendationComposer


def test_recommendation_card_composition():
    """Verify recommendation card formatting, trade-offs, confidence, and propensity score."""
    composer = RecommendationComposer()

    causal_ctx = {
        "competitor_payout_rate": 0.42,
        "partner_churn_rate": 0.18,
        "ftd_count_28d": 1200.0,
    }

    card = composer.compose_recommendation(
        action_type="AdjustPartnerTier",
        target_entity_id="P-101",
        impact_estimate=(8000.0, 15000.0),
        impact_unit="USD",
        pros=[
            "Directly mitigates partner churn hazard in Tier 1 affiliate cohort",
            "Preserves estimated $11,500 monthly net deposit volume",
        ],
        cons=[
            "Increases immediate monthly payout commission by 3.5%",
            "Requires bilateral agreement amendment within 14 business days",
        ],
        confidence=0.88,
        evidence_citations=["partner_churn_rate", "net_deposit_volume_usd"],
        causal_context=causal_ctx,
    )

    assert isinstance(card, RecommendationCard)
    assert card.recommendation_id.startswith("REC-")
    assert card.action_type == "AdjustPartnerTier"
    assert card.target_entity_id == "P-101"
    assert card.impact_estimate_min == 8000.0
    assert card.impact_estimate_max == 15000.0
    assert card.impact_unit == "USD"
    assert len(card.pros) >= 2
    assert len(card.cons) >= 2
    assert card.confidence >= 0.80
    assert 0.01 <= card.propensity_score <= 0.99
    assert len(card.evidence_citations) >= 1
    assert card.causal_context == causal_ctx


def test_action_intent_proposal_emission_without_direct_execution():
    """Verify that proposing action emits a signed pending ActionIntentToken with no direct write sinks."""
    hub = ActionIntentHub()
    composer = RecommendationComposer(intent_hub=hub)

    card = composer.compose_recommendation(
        action_type="AdjustPartnerTier",
        target_entity_id="P-101",
        impact_estimate=(5000.0, 10000.0),
        impact_unit="USD",
        pros=["Improves partner retention", "Recovers lost commission"],
        cons=["Commission increase", "Margin compression"],
        confidence=0.85,
        evidence_citations=["partner_churn_rate"],
        causal_context={"partner_churn_rate": 0.22},
    )

    token = composer.propose_action_intent(
        card=card,
        parameters={"partner_id": "P-101", "target_tier": "TIER_1"},
    )

    assert isinstance(token, ActionIntentToken)
    assert token.status == ActionStatus.PENDING
    assert token.action_type == "AdjustPartnerTier"
    assert token.parameters["partner_id"] == "P-101"
    assert token.signature is not None
    assert token.propensity_score == card.propensity_score
    # Invariant: No mutation execution took place
    assert len(token.approvals) == 0
