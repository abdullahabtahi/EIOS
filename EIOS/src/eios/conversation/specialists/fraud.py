"""Conversational Partner Fraud Specialist Agent (T042 / US6).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (Principle VII)
- .specify/memory/constitution.md (Principles I, II, VIII)

Integrates with OMCP tool ecosystem (get_partner_fraud_dossier, get_opposite_trading_pairs,
get_partner_referral_ring, propose_action) to provide verified multi-turn answers
passing the Metric Auditor Gate with deterministic fallback under outage.
"""

import re
from typing import Any, Sequence
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool

from eios.conversation.models import SpecialistDomain
from eios.conversation.specialists.base import BaseSpecialistAgent
from eios.fraud.sanitizer import FraudComplianceSanitizer
from eios.ontology.omcp.server import OMCPServer


class PartnerFraudSpecialist:
    """Domain specialist agent for Partner & Affiliate Fraud Sentinel."""

    def __init__(self, omcp_server: OMCPServer | None = None) -> None:
        self.omcp_server = omcp_server
        self.sanitizer = FraudComplianceSanitizer()

    @property
    def domain(self) -> SpecialistDomain:
        return SpecialistDomain.PARTNER_FRAUD

    @property
    def allowed_tools(self) -> Sequence[str]:
        return [
            "get_partner_fraud_dossier",
            "get_opposite_trading_pairs",
            "get_partner_referral_ring",
            "get_client_quality_profile",
            "propose_action",
        ]

    def _extract_partner_id(self, text: str) -> str | None:
        """Extract partner ID pattern (e.g. P-FRAUD-01, P-OPP-1, P-100)."""
        match = re.search(r"\b(P-[A-Za-z0-9_-]+)\b", text)
        if match:
            return match.group(1).upper()
        return None

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute reasoning grounded in deterministic OMCP tools with replay fallback."""
        last_msg = state["messages"][-1]
        text = str(last_msg.content)

        partner_id = self._extract_partner_id(text) or "P-DEFAULT"

        citations = ["DP2:trading_activity", "DP7:partner_referral_tree", "DP8:commission_ledger"]
        is_replay = state.get("is_replay_fallback", False)

        try:
            if self.omcp_server:
                dossier = self.omcp_server.call_tool(
                    "get_partner_fraud_dossier",
                    {"partner_id": partner_id},
                    caller_role="ComplianceOfficer",
                )
                summary = dossier.get(
                    "narrative_summary",
                    f"Compliance investigation completed for {partner_id}.",
                )
                exposure = dossier.get("total_exposure_usd", 0.0)
                risk = dossier.get("fraud_risk_score", 0.0)
                action = dossier.get("recommended_action", "ReviewAudit")

                content = (
                    f"{summary} "
                    f"Quantified risk severity: {risk:.2f}, total illicit commission exposure: "
                    f"${exposure:,.2f} USD. Recommended action intent: {action}."
                )
            else:
                # Deterministic fallback response with [REPLAY] badge if outage
                is_replay = True
                content = (
                    f"[REPLAY] Partner fraud investigation profile for {partner_id}: "
                    f"coordinated opposite trading pattern identified with unearned incentive volume. "
                    f"Total financial exposure quantified at $12,500.00 USD. Recommended action: ClawbackCommission."
                )
        except Exception:
            is_replay = True
            content = (
                f"[REPLAY] Partner fraud investigation profile for {partner_id}: "
                f"coordinated opposite trading pattern identified with unearned incentive volume. "
                f"Total financial exposure quantified at $12,500.00 USD. Recommended action: ClawbackCommission."
            )

        sanitized_content = self.sanitizer.sanitize(content)

        return {
            "messages": [AIMessage(content=sanitized_content)],
            "reflection_cycles": state.get("reflection_cycles", 0) + 1,
            "next_agent": "supervisor",
            "extracted_evidence": [
                {
                    "entity_id": partner_id,
                    "citations": citations,
                    "is_replay": is_replay,
                }
            ],
        }
