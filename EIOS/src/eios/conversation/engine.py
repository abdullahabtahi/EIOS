from langchain_core.messages import HumanMessage

from eios.conversation.graph import create_conversational_graph
from eios.conversation.models import (
    ConversationQueryRequest,
    ConversationQueryResponse,
    RouteDecision,
    SpecialistDomain,
)
from eios.llm_gateway.gateway import Gateway
from eios.ontology.auditor.gate import MetricAuditorGate


class ConversationEngine:
    """
    Facade for interacting with the Conversational Multi-Agent Reasoning Mesh.
    """

    def __init__(self, gateway: Gateway, auditor: MetricAuditorGate):
        self.workflow = create_conversational_graph(gateway, auditor)

    def query(self, request: ConversationQueryRequest) -> ConversationQueryResponse:
        """Execute a conversational turn through the LangGraph mesh."""
        # T020 & T021 & T022: Speculative Query Refusal Short-circuit
        # A real implementation would invoke an LLM router here to get a RouteDecision
        # For demonstration, we implement a simple keyword based short-circuit.
        if "speculative" in request.user_query.lower() or "guess" in request.user_query.lower():
            decision = RouteDecision(
                route=SpecialistDomain.SYNTHESIS,
                confidence=1.0,
                rationale="Query asks for speculative guesses without data.",
                refusal_required=True,
                refusal_reason="insufficient data",
            )
            return ConversationQueryResponse(
                session_id=request.session_id or "new_session",
                turn_index=1,
                route=decision.route,
                response_markdown="I cannot answer this query due to insufficient data.",
                citations=[],
                evidence_ledger=[],
                staged_recommendation=None,
                is_replay_fallback=False,
                turn_latency_ms=0.0,
                reflection_cycles_used=0,
            )

        initial_state = {
            "messages": [HumanMessage(content=request.user_query)],
            "next_agent": "supervisor",
            "reflection_cycles": 0,
            "extracted_evidence": [],
            "staged_actions": [],
            "final_response": "",
        }

        # In a real setup, we would pass thread_id for persistence
        config = {"configurable": {"thread_id": request.session_id or "new_session"}}

        result_state = self.workflow.invoke(initial_state, config=config)

        staged_actions = result_state.get("staged_actions", [])
        staged_recommendation = staged_actions[0] if staged_actions else None

        return ConversationQueryResponse(
            session_id=request.session_id or "new_session",
            turn_index=1,
            route=SpecialistDomain.SYNTHESIS,  # Simplification, in reality track which agents executed
            response_markdown=result_state.get("final_response", ""),
            citations=[],
            evidence_ledger=[],
            staged_recommendation=staged_recommendation,
            is_replay_fallback=False,
            turn_latency_ms=0.0,
            reflection_cycles_used=result_state.get("reflection_cycles", 0),
        )
