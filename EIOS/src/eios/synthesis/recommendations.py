"""Governed Recommendation Composer and Action Intent proposal emission (US5, FR-020-FR-023)."""

import uuid
from typing import Any

from eios.ontology.actions.intent_hub import ActionIntentHub, ActionIntentToken
from eios.synthesis.aipw import compute_propensity_score
from eios.synthesis.models import RecommendationCard


class RecommendationComposer:
    """Human-in-the-loop recommendation builder and Action Intent token proposer."""

    def __init__(self, intent_hub: ActionIntentHub | None = None) -> None:
        self.intent_hub = intent_hub or ActionIntentHub()

    def compose_recommendation(  # noqa: PLR0913
        self,
        action_type: str,
        target_entity_id: str,
        impact_estimate: tuple[float, float],
        impact_unit: str = "USD",
        pros: list[str] | None = None,
        cons: list[str] | None = None,
        confidence: float = 0.85,
        evidence_citations: list[str] | None = None,
        causal_context: dict[str, float] | None = None,
    ) -> RecommendationCard:
        """Compose a structured recommendation decision card with trade-offs and propensity logging."""
        ctx = causal_context or {}
        evidence = evidence_citations or []
        pro_list = pros or [
            "Reduces downstream revenue degradation",
            "Stabilizes partner referral channel",
        ]
        con_list = cons or [
            "Incurs short-term budget expenditure",
            "Requires compliance operations review",
        ]

        # Calculate bounded propensity score e(X) in [0.01, 0.99]
        propensity = compute_propensity_score(ctx)

        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"

        return RecommendationCard(
            recommendation_id=rec_id,
            action_type=action_type,
            target_entity_id=target_entity_id,
            impact_estimate_min=float(impact_estimate[0]),
            impact_estimate_max=float(impact_estimate[1]),
            impact_unit=impact_unit,
            pros=pro_list,
            cons=con_list,
            confidence=max(0.0, min(1.0, float(confidence))),
            evidence_citations=evidence,
            propensity_score=propensity,
            causal_context=ctx,
        )

    def propose_action_intent(
        self,
        card: RecommendationCard,
        parameters: dict[str, Any],
        requester_agent_id: str = "ExecutiveSynthesisAgent",
    ) -> ActionIntentToken:
        """Propose an action intent via ActionIntentHub, emitting signed token without direct writes."""
        return self.intent_hub.propose_action(
            action_type=card.action_type,
            parameters=parameters,
            evidence_refs=card.evidence_citations,
            requester_agent_id=requester_agent_id,
            propensity_score=card.propensity_score,
            causal_context=card.causal_context,
        )
