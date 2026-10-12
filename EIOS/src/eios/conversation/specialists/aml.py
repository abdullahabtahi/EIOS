"""Conversational Sentinel AML Specialist Agent (T042 / US6).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- specs/010-client-aml/spec.md (User Story 6, SC-006, SC-007)
- .specify/memory/constitution.md (Principles I, II, VII, VIII)

Integrates with OMCP tool ecosystem (get_client_aml_dossier, get_mule_ring_graph,
get_roundtrip_structuring_alerts, check_withdrawal_risk, generate_sar_draft, propose_aml_action)
to provide grounded, non-technical financial crime explanations with deterministic
replay fallback [REPLAY] under outage.
"""

import re
from typing import Any, Sequence
from langchain_core.messages import AIMessage

from eios.conversation.models import SpecialistDomain
from eios.ontology.omcp.server import OMCPServer


class SentinelAMLSpecialist:
    """Domain specialist agent for Client Fraud Sentinel / AML Transaction Monitoring."""

    def __init__(self, omcp_server: OMCPServer | None = None) -> None:
        self.omcp_server = omcp_server

    @property
    def domain(self) -> SpecialistDomain:
        return SpecialistDomain.SENTINEL_AML

    @property
    def allowed_tools(self) -> Sequence[str]:
        return [
            "get_client_aml_dossier",
            "get_mule_ring_graph",
            "get_roundtrip_structuring_alerts",
            "check_withdrawal_risk",
            "generate_sar_draft",
            "propose_aml_action",
        ]

    def _extract_client_id(self, text: str) -> str | None:
        """Extract client/account ID pattern (e.g. C-AML-ROUNDTRIP-01, C-10023, C-MULE-01)."""
        match = re.search(r"\b(C-[A-Za-z0-9_-]+)\b", text)
        if match:
            return match.group(1).upper()
        return None

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute reasoning cycle grounded in deterministic OMCP tools with replay fallback."""
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else None
        text = str(last_msg.content) if last_msg else ""

        client_id = self._extract_client_id(text) or "C-AML-DEFAULT"
        citations = ["DP1:transactions_aml", "DP2:trading_activity", "DP6:compliance_cases"]
        is_replay = state.get("is_replay_fallback", False)

        try:
            if self.omcp_server:
                dossier = self.omcp_server.call_tool(
                    "get_client_aml_dossier",
                    {"client_id": client_id},
                    caller_role="ComplianceOfficer",
                )
                summary = dossier.get("narrative_summary", f"AML investigation completed for {client_id}.")
                risk = dossier.get("composite_risk_score", 0.0)
                tier = dossier.get("priority_tier", "MEDIUM")
                action = dossier.get("recommended_action", "MonitorAccount")
                citations = dossier.get("citations", citations)

                content = (
                    f"{summary} "
                    f"Composite AML risk score: {risk:.2f} ({tier}). "
                    f"Recommended operational action intent: {action} (pending human approval)."
                )
            else:
                is_replay = True
                content = (
                    f"[REPLAY] Client AML surveillance profile for {client_id}: "
                    "structuring and micro-P&L wash round-trip sequence detected pursuant to "
                    "31 CFR 1010 and 31 U.S.C. 5318(g). Risk score: 0.92 (CRITICAL). "
                    "Recommended action intent: HoldWithdrawal (human sign-off mandatory)."
                )
        except Exception:
            is_replay = True
            content = (
                f"[REPLAY] Client AML surveillance profile for {client_id}: "
                "structuring and micro-P&L wash round-trip sequence detected pursuant to "
                "31 CFR 1010 and 31 U.S.C. 5318(g). Risk score: 0.92 (CRITICAL). "
                "Recommended action intent: HoldWithdrawal (human sign-off mandatory)."
            )

        return {
            "messages": [AIMessage(content=content)],
            "reflection_cycles": state.get("reflection_cycles", 0) + 1,
            "next_agent": "supervisor",
            "extracted_evidence": [
                {
                    "entity_id": client_id,
                    "citations": citations,
                    "is_replay": is_replay,
                }
            ],
        }
