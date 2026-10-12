"""SupervisoryRouter for Conversational Reasoning Mesh (US6 / FR-013, FR-014).

Authoritative References:
- specs/011-governed-actions-ledger/spec.md (User Story 6, SC-007)
- .specify/memory/constitution.md (Principles I, II, IV, VIII)
"""

from typing import Any
from eios.conversation.models import RouteDecision, SpecialistDomain
from eios.conversation.specialists.governance import GovernanceAuditorSpecialist


class SupervisoryRouter:
    """Supervisory Router directing conversational intent and audit queries to domain specialists."""

    def __init__(self, specialists: dict[SpecialistDomain, Any] | None = None) -> None:
        self.specialists = specialists or {
            SpecialistDomain.GOVERNANCE: GovernanceAuditorSpecialist(),
        }

    def route_query(self, query: str, context: dict[str, Any] | None = None) -> RouteDecision:
        """Route user query to appropriate specialist domain."""
        text = query.lower()

        if any(term in text for term in ["governance", "ledger", "audit", "hash chain", "action intent", "four-eyes"]):
            return RouteDecision(
                route=SpecialistDomain.GOVERNANCE,
                confidence=0.98,
                rationale="Query asks for action ledger governance, cryptographic audit, or Four-Eyes verification.",
            )
        elif any(term in text for term in ["aml", "laundering", "mule", "structuring"]):
            return RouteDecision(
                route=SpecialistDomain.SENTINEL_AML,
                confidence=0.95,
                rationale="Query asks for anti-money laundering investigation.",
            )
        elif any(term in text for term in ["fraud", "affiliate", "collusion", "bonus abuse"]):
            return RouteDecision(
                route=SpecialistDomain.PARTNER_FRAUD,
                confidence=0.95,
                rationale="Query asks for partner fraud investigation.",
            )
        elif any(term in text for term in ["churn", "retention", "hazard"]):
            return RouteDecision(
                route=SpecialistDomain.CHURN_RADAR,
                confidence=0.95,
                rationale="Query asks for partner churn telemetry.",
            )
        elif any(term in text for term in ["forecast", "briefing", "synthesis", "scenario"]):
            return RouteDecision(
                route=SpecialistDomain.SYNTHESIS,
                confidence=0.90,
                rationale="Query asks for executive briefing, forecast, or causal scenario.",
            )
        else:
            return RouteDecision(
                route=SpecialistDomain.SYNTHESIS,
                confidence=0.50,
                rationale="Default synthesis routing fallback.",
            )

    def get_specialist(self, domain: SpecialistDomain) -> Any:
        """Retrieve specialist instance registered for domain."""
        return self.specialists.get(domain)
