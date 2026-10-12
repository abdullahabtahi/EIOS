"""Domain specialist agents with strict tool allow-lists (QuantumBlack topology, T029)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List
from eios.conversation.rag_tools import query_policy_search, query_sar_precedents
from eios.conversation.tools import (
    get_governed_metric,
    inspect_aml_entity,
    inspect_partner_churn,
    query_graph_topology,
    run_causal_what_if,
    stage_action_intent,
)


class SpecialistAgent:
    """Base class for domain specialists in the conversational mesh."""

    def __init__(self, name: str, allowed_tools: List[Callable[..., Any]], system_prompt: str) -> None:
        self.name = name
        self.allowed_tools = {t.__name__: t for t in allowed_tools}
        self.system_prompt = system_prompt

    def execute_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute a tool strictly validated against the specialist's allow-list."""
        if tool_name not in self.allowed_tools:
            raise PermissionError(f"Specialist '{self.name}' is not authorized to call tool '{tool_name}'")
        return self.allowed_tools[tool_name](**kwargs)


# 1. Executive Synthesis Specialist
EXECUTIVE_SYNTHESIS = SpecialistAgent(
    name="executive_synthesis",
    allowed_tools=[get_governed_metric, run_causal_what_if],
    system_prompt="Synthesize top-level enterprise KPIs and causal scenarios for executive decision makers.",
)

# 2. AML Investigator Specialist (SR 11-7 Forensic Objectivity enforced)
AML_INVESTIGATOR = SpecialistAgent(
    name="aml_investigator",
    allowed_tools=[
        inspect_aml_entity,
        query_graph_topology,
        query_policy_search,
        query_sar_precedents,
        stage_action_intent,
    ],
    system_prompt=(
        "Forensic AML investigation specialist. Objectively report KYC discrepancy multipliers, "
        "deposit velocity, and syndicate ring connections under 31 CFR § 1020.320."
    ),
)

# 3. Partner Retention Specialist
PARTNER_RETENTION = SpecialistAgent(
    name="partner_retention",
    allowed_tools=[inspect_partner_churn, get_governed_metric, stage_action_intent],
    system_prompt="Evaluate partner turnover, hazard scores, and retention playbooks.",
)

# 4. Partner Fraud Specialist
PARTNER_FRAUD = SpecialistAgent(
    name="partner_fraud",
    allowed_tools=[inspect_aml_entity, query_graph_topology],
    system_prompt="Investigate affiliate collusion and opposite-side trading rings.",
)

# 5. Governance & Compliance Specialist
GOVERNANCE_COMPLIANCE = SpecialistAgent(
    name="governance_compliance",
    allowed_tools=[query_policy_search, query_sar_precedents],
    system_prompt="Audit statutory rules, FinCEN precedents, and WORM decision ledger proofs.",
)

ALL_SPECIALISTS = {
    "executive_synthesis": EXECUTIVE_SYNTHESIS,
    "aml_investigator": AML_INVESTIGATOR,
    "partner_retention": PARTNER_RETENTION,
    "partner_fraud": PARTNER_FRAUD,
    "governance_compliance": GOVERNANCE_COMPLIANCE,
}
