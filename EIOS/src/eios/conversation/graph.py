"""LangGraph Supervisor Pattern and Action Execution Sink (US5, FR-021)."""

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, StateGraph

from eios.conversation.auditor_bridge import ConversationAuditorBridge
from eios.conversation.memory import ConversationMemoryManager
from eios.conversation.specialists.aml import SentinelAMLSpecialist
from eios.conversation.specialists.churn import ChurnRadarSpecialist
from eios.conversation.specialists.fraud import PartnerFraudSpecialist
from eios.conversation.specialists.governance import GovernanceAuditorSpecialist
from eios.llm_gateway.gateway import Gateway
from eios.llm_gateway.models import GatewayRequest
from eios.ontology.auditor.gate import MetricAuditorGate


class BlackboardState(TypedDict):
    """LangGraph shared state matching the Blackboard topology."""

    messages: Annotated[list[BaseMessage], operator.add]
    next_agent: str
    reflection_cycles: int
    extracted_evidence: list[dict[str, Any]]
    final_response: str
    staged_actions: list[dict[str, Any]]


class ActionExecutionSink:
    """Stages non-autonomous recommendation cards with zero direct database write execution."""

    def __init__(self) -> None:
        self.staged_cards: list[dict[str, Any]] = []

    def stage_action(self, action_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Stage an action for human review instead of executing it directly."""
        card = {
            "type": "RecommendationCard",
            "action": action_type,
            "payload": payload,
            "status": "STAGED_FOR_REVIEW",
        }
        self.staged_cards.append(card)
        return card


def create_conversational_graph(gateway: Gateway, auditor: MetricAuditorGate) -> StateGraph:  # noqa: C901, PLR0915
    """Build the conversational multi-agent mesh using LangGraph."""

    ActionExecutionSink()
    bridge = ConversationAuditorBridge(auditor)
    memory_manager = ConversationMemoryManager()

    def supervisor_node(state: BlackboardState) -> dict[str, Any]:
        """Supervisory Router: decides next agent or finishes."""
        if state.get("reflection_cycles", 0) >= 3:
            return {"next_agent": "FINISH"}

        # T024: Statutory compliance arbitration
        if state.get("compliance_hold", False) and state.get("staged_actions", []):
            return {
                "next_agent": "FINISH",
                "final_response": "Action blocked due to active AML/Sanctions compliance hold.",
            }

        # Compact context
        compacted = memory_manager.compact_context(state["messages"])
        last_msg = compacted[-1]

        # Resolve pronominal entities based on anchors (mocked)
        anchors = state.get("entity_anchors", {})
        query = memory_manager.resolve_pronominal_entities(str(last_msg.content), anchors)
        text = query.lower()

        # Simple fallback routing logic for demonstration
        if "forecast" in text or "synthesis" in text:
            return {"next_agent": "synthesis"}
        elif "aml" in text or "laundering" in text:
            return {"next_agent": "aml"}
        elif "churn" in text or "retention" in text:
            return {"next_agent": "churn"}
        elif "fraud" in text or "affiliate" in text:
            return {"next_agent": "fraud"}
        elif "governance" in text or "ledger" in text or "audit" in text or "hash chain" in text:
            return {"next_agent": "governance"}
        else:
            return {"next_agent": "FINISH"}

    def synthesis_node(state: BlackboardState) -> dict[str, Any]:
        """Synthesis Specialist node generating response via Gateway."""
        req = GatewayRequest(
            prompt_id="prompt.synthesis.specialist",
            prompt_version="1",
            inputs={"context": str(state["messages"][-1].content)},
            correlation_id="corr_synthesis_conv",
            caller="conversation.synthesis",
        )

        # Wrap calls in Gateway.complete
        try:
            resp = gateway.complete(req)
            content = resp.content or "Synthesis response generated."
        except Exception:
            content = "Synthesis fallback response."

        return {
            "messages": [AIMessage(content=content)],
            "reflection_cycles": state.get("reflection_cycles", 0) + 1,
            "next_agent": "supervisor",
        }

    def aml_node(state: BlackboardState) -> dict[str, Any]:
        """AML Specialist node."""
        agent = SentinelAMLSpecialist()
        return agent.invoke(state)

    def churn_node(state: BlackboardState) -> dict[str, Any]:
        """Churn Specialist node."""
        agent = ChurnRadarSpecialist()
        return agent.invoke(state)

    def fraud_node(state: BlackboardState) -> dict[str, Any]:
        """Fraud Specialist node."""
        agent = PartnerFraudSpecialist()
        return agent.invoke(state)

    def governance_node(state: BlackboardState) -> dict[str, Any]:
        """Governance Specialist node."""
        agent = GovernanceAuditorSpecialist(omcp_server=state.get("omcp_server"))
        return agent.invoke(state)

    def egress_firewall(state: BlackboardState) -> dict[str, Any]:
        """Final output scanner via MetricAuditorGate (Principle I)."""
        last_msg = state["messages"][-1]
        text = str(last_msg.content)

        safe_text = bridge.scan_egress_response(
            response_text=text, evidence_ledger=state.get("extracted_evidence", [])
        )

        return {"final_response": safe_text}

    workflow = StateGraph(BlackboardState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("aml", aml_node)
    workflow.add_node("churn", churn_node)
    workflow.add_node("fraud", fraud_node)
    workflow.add_node("governance", governance_node)
    workflow.add_node("egress", egress_firewall)

    workflow.set_entry_point("supervisor")

    def route(state: BlackboardState) -> str:
        if state["next_agent"] == "FINISH":
            return "egress"
        return state["next_agent"]

    workflow.add_conditional_edges(
        "supervisor",
        route,
        {
            "synthesis": "synthesis",
            "aml": "aml",
            "churn": "churn",
            "fraud": "fraud",
            "governance": "governance",
            "egress": "egress",
        },
    )

    workflow.add_edge("synthesis", "supervisor")
    workflow.add_edge("aml", "supervisor")
    workflow.add_edge("churn", "supervisor")
    workflow.add_edge("fraud", "supervisor")
    workflow.add_edge("governance", "supervisor")
    workflow.add_edge("egress", END)

    return workflow.compile()
