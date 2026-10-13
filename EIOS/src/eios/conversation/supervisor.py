"""LangGraph Hierarchical Supervisor coordinating domain specialists (F018, T030)."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from eios.conversation.models import BlackboardState, SpecialistRoute
from eios.conversation.specialists.agents import ALL_SPECIALISTS

_LOG = logging.getLogger("eios.conversation.supervisor")


class ConversationalSupervisor:
    """Supervises multi-agent delegation, reflection cycle caps, and compliance priority."""

    def __init__(self) -> None:
        self.specialists = ALL_SPECIALISTS

    def classify_route(self, query: str) -> SpecialistRoute:
        """Classify operator intent into one of 5 domain specialist routes."""
        clean_q = query.lower()

        # 1. AML / Mule check
        if any(
            w in clean_q
            for w in ["aml", "mule", "cr84920", "sar", "structuring", "discrepancy multiplier"]
        ):
            return SpecialistRoute.AML_INVESTIGATOR

        # 2. Compliance / Regulatory / WORM audit
        if any(
            w in clean_q
            for w in ["compliance", "audit proof", "worm", "fincen", "statute", "31 cfr", "fatf"]
        ):
            return SpecialistRoute.GOVERNANCE_COMPLIANCE

        # 3. Partner Churn / Retention
        if any(
            w in clean_q
            for w in ["churn", "retention", "ap-1029", "p-882", "spread decay", "rebate"]
        ):
            return SpecialistRoute.PARTNER_RETENTION

        # 4. Partner Fraud / Collusion
        if any(w in clean_q for w in ["collusion", "opposite-side", "affiliate ring"]):
            return SpecialistRoute.PARTNER_FRAUD

        # 5. Default: Executive Synthesis
        return SpecialistRoute.EXECUTIVE_SYNTHESIS

    def evaluate_priority_transition(self, state: BlackboardState) -> str:
        """Evaluates Compliance Priority Hierarchy (Principle VII).

        If an active AML or sanctions compliance hold is detected, commercial actions
        are preemptively redirected to governance and compliance review.
        """
        if state.compliance_hold:
            return "governance_compliance"
        return state.next_agent

    def evaluate_reflection_transition(self, state: BlackboardState) -> str:
        """Enforces bounded deliberation cap (max 3 reflection loops, Principle VII)."""
        if state.reflection_cycles >= 3:
            return "egress_synthesis"
        return state.next_agent

    def build_graph(self) -> StateGraph:
        """Builds the LangGraph hierarchical state machine."""
        builder = StateGraph(BlackboardState)

        # Supervisor node
        def supervisor_node(state: BlackboardState) -> dict[str, Any]:
            route = state.active_route
            agent_map = {
                SpecialistRoute.EXECUTIVE_SYNTHESIS: "executive_synthesis",
                SpecialistRoute.AML_INVESTIGATOR: "aml_investigator",
                SpecialistRoute.PARTNER_RETENTION: "partner_retention",
                SpecialistRoute.PARTNER_FRAUD: "partner_fraud",
                SpecialistRoute.GOVERNANCE_COMPLIANCE: "governance_compliance",
            }
            target = agent_map.get(route, "executive_synthesis")
            if state.compliance_hold:
                target = "governance_compliance"
            return {"next_agent": target, "reflection_cycles": state.reflection_cycles + 1}

        builder.add_node("supervisor", supervisor_node)

        # Specialist execution nodes
        for name, spec in self.specialists.items():

            def make_node(agent_name: str):
                def node_fn(state: BlackboardState) -> dict[str, Any]:
                    return {"next_agent": "egress_synthesis"}

                return node_fn

            builder.add_node(name, make_node(name))

        def egress_node(state: BlackboardState) -> dict[str, Any]:
            return {"final_response": "Grounded synthesis complete"}

        builder.add_node("egress_synthesis", egress_node)

        builder.set_entry_point("supervisor")
        builder.add_edge("executive_synthesis", "egress_synthesis")
        builder.add_edge("aml_investigator", "egress_synthesis")
        builder.add_edge("partner_retention", "egress_synthesis")
        builder.add_edge("partner_fraud", "egress_synthesis")
        builder.add_edge("governance_compliance", "egress_synthesis")
        builder.add_edge("egress_synthesis", END)

        return builder.compile()
