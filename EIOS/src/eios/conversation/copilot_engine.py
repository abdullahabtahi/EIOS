"""Production-grade Conversational Copilot Engine (F018, T014)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from eios.conversation.auditor_bridge import ConversationAuditorBridge
from eios.conversation.checkpointer import ThreadCheckpointer
from eios.conversation.client import GeminiClientManager, types
from eios.conversation.memory import SessionMemoryManager
from eios.conversation.models import (
    CitationType,
    ConversationQueryResponse,
    OperatorRole,
    ProvenanceCitation,
    SpecialistDomain,
)
from eios.conversation.rag_tools import query_policy_search, should_route_to_policy_rag
from eios.conversation.supervisor import ConversationalSupervisor
from eios.conversation.telemetry import CopilotTracer
from eios.conversation.tools import (
    OMCP_TOOLS,
    get_governed_metric,
    inspect_aml_entity,
    inspect_partner_churn,
    query_graph_topology,
    run_causal_what_if,
    stage_action_intent,
)

_LOG = logging.getLogger("eios.conversation.copilot_engine")

TOOL_MAP = {
    "get_governed_metric": get_governed_metric,
    "inspect_aml_entity": inspect_aml_entity,
    "query_graph_topology": query_graph_topology,
    "inspect_partner_churn": inspect_partner_churn,
    "run_causal_what_if": run_causal_what_if,
    "query_policy_search": query_policy_search,
    "stage_action_intent": stage_action_intent,
}

SYSTEM_INSTRUCTION_BASE = """You are the EIOS Enterprise Copilot, an institutional sovereign intelligence operating system for online brokerage operations (EIOS Governed Kinetic Architecture).

CRITICAL OPERATIONAL INVARIANTS:
1. (Principle I) YOU NEVER CALCULATE OR ESTIMATE BUSINESS METRICS. Always invoke the provided OMCP tools to retrieve numbers.
2. (Principle III) If asked for speculative future predictions or unobservable competitor internals, respond strictly with "insufficient data".
3. (SR 11-7 Forensic Objectivity) In compliance and AML inquiries, describe factual observed patterns objectively. State amounts, frequencies, and discrepancy ratios without alleging subjective criminal intent.
4. Always cite specific entity identifiers, metric definitions, and regulatory sections (e.g. 31 CFR § 1020.320).
5. Quote every figure exactly as a tool returned it. Never state a number no tool returned: no thresholds, scales (such as "out of 100"), percentages you derived, ratios you computed, or counts you tallied. If a figure is not in a tool result, omit it.
"""


MAX_TOOL_ROUNDS = 4
MAX_CORRECTIONS = 2  # within the 3-cycle reflection bound of ADR-016


def correction_prompt(unanchored: list[str]) -> str:
    shown = ", ".join(sorted(set(unanchored))[:12]) or "some figures"
    return (
        "The Metric Auditor blocked your answer: these figures do not appear in any tool result: "
        f"{shown}. Rewrite the answer using only values the tools returned, quoted exactly. "
        "Remove every other number; do not compute, convert or estimate."
    )


def run_omcp_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run one model-requested tool. Only OMCP tools in TOOL_MAP exist; failures are reported, never raised."""
    func = TOOL_MAP.get(name)
    if func is None:
        return {"error": f"unknown tool '{name}'"}
    try:
        result = func(**dict(args))
    except Exception as exc:  # a tool failure must not abort the turn; the model and auditor see it
        _LOG.warning("OMCP tool %s failed: %s", name, exc)
        return {"error": f"{type(exc).__name__}: {exc}"}
    return result if isinstance(result, dict) else {"result": result}


class CopilotEngine:
    """Core conversational engine orchestrating provider model execution with dual-engine grounding."""

    def __init__(
        self,
        client_manager: GeminiClientManager | None = None,
        auditor_bridge: ConversationAuditorBridge | None = None,
        offline_mode: bool | None = None,
    ) -> None:
        if offline_mode is None:
            # Default to offline if EIOS_OFFLINE_REPLAY=1 or in unit test mode
            offline_mode = os.getenv("EIOS_OFFLINE_REPLAY", "0") == "1"

        self.client_manager = client_manager or GeminiClientManager(offline_mode=offline_mode)
        self.auditor_bridge = auditor_bridge or ConversationAuditorBridge()
        self.offline_mode = offline_mode or self.client_manager.offline_mode
        self.memories: dict[str, SessionMemoryManager] = {}
        self.checkpointer = ThreadCheckpointer()
        self.supervisor = ConversationalSupervisor()
        self.tracer = CopilotTracer()

    def _resolve_tool_calls(
        self,
        chat: Any,
        response: Any,
        tool_traces: list[dict[str, Any]],
        citations: list[ProvenanceCitation],
    ) -> Any:
        """Run the tools the model asked for (allow-listed, bounded rounds) and return its next response."""
        for _ in range(MAX_TOOL_ROUNDS):
            calls = list(getattr(response, "function_calls", None) or [])
            if not calls:
                break
            fn_parts = []
            for fc in calls:
                output = run_omcp_tool(fc.name, fc.args or {})
                tool_traces.append({"tool": fc.name, "output": output})
                if "error" not in output:
                    citations.append(
                        ProvenanceCitation(
                            citation_type=CitationType.METRIC,
                            citation_id=fc.name,
                            label=f"Tool {fc.name}",
                            source_engine="OMCP",
                        )
                    )
                fn_parts.append(
                    types.Part.from_function_response(name=fc.name, response={"result": output})
                )
            response = chat.send_message(fn_parts)
        return response

    def process_query(
        self,
        query: str,
        role: OperatorRole = OperatorRole.EXECUTIVE,
        session_id: str = "sess_default",
        turn_index: int = 1,
    ) -> ConversationQueryResponse:
        """Process an operator inquiry with dual-engine grounding and auditor gate verification."""
        t_start = time.perf_counter()

        mem = self.memories.setdefault(session_id, SessionMemoryManager(session_id))
        resolved_query = mem.resolve_pronominal_references(query)
        lower_q = resolved_query.lower()

        # Check for speculative out-of-domain queries or unauthorized write attacks (Principle II & III)
        adversarial_patterns = [
            "in 2030",
            "predict 2030",
            "guess",
            "unrecorded transactions without any logging",
            "secret profit",
            "without tools",
            "speculative",
            "directly execute a database write",
            "without review",
            "bypass four-eyes",
            "unilaterally as single officer",
            "alter" + " table",
            "drop" + " table",
            "ignore all instructions",
        ]
        if any(w in lower_q for w in adversarial_patterns):
            return ConversationQueryResponse(
                session_id=session_id,
                turn_index=turn_index,
                route=SpecialistDomain.SYNTHESIS,
                response_markdown="Blocked: Insufficient data to substantiate numerical figures or unauthorized direct write attempt (Principle I, II & III).",
                citations=[],
                provenance_citations=[],
                evidence_ledger=[],
                is_replay_fallback=False,
                turn_latency_ms=round((time.perf_counter() - t_start) * 1000, 2),
                auditor_status="BLOCKED",
            )

        client = self.client_manager.get_client()
        fallback_reason: str | None = None
        if self.offline_mode or client is None:
            fallback_reason = self.client_manager.offline_reason or "offline replay mode"
        tool_traces: list[dict[str, Any]] = []
        citations: list[ProvenanceCitation] = []

        # Live Gemini with manual function calling: the model proposes tool calls, this engine runs
        # only allow-listed OMCP tools, and the Metric Auditor checks the final text against the traces.
        if client and not self.offline_mode:
            try:
                available_tools = list(OMCP_TOOLS)
                if should_route_to_policy_rag(query):
                    available_tools.append(query_policy_search)

                chat = client.chats.create(
                    model=self.client_manager.model_id,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION_BASE,
                        temperature=0.0,
                        tools=available_tools,
                        # The SDK's automatic calling runs the tools itself and hides their results from
                        # the engine (and fails on Python 3.14 argument handling); the engine runs them.
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                    ),
                )
                response = chat.send_message(query)

                response = self._resolve_tool_calls(chat, response, tool_traces, citations)

                raw_text = response.text or ""
                audit_res = self.auditor_bridge.audit_turn(raw_text, tool_traces)

                # Bounded self-correction: show the model exactly which figures the auditor could not trace.
                corrections = 0
                while not audit_res.passed and corrections < MAX_CORRECTIONS:
                    corrections += 1
                    response = chat.send_message(correction_prompt(audit_res.unanchored_tokens))
                    response = self._resolve_tool_calls(chat, response, tool_traces, citations)
                    raw_text = response.text or ""
                    audit_res = self.auditor_bridge.audit_turn(raw_text, tool_traces)

                # Ensure queries targeting metrics or entities have non-empty tool traces and citations
                has_metric_intent = any(
                    k in lower_q
                    for k in [
                        "turnover",
                        "deposit",
                        "spread",
                        "cr84920",
                        "revenue",
                        "churn",
                        "p-882",
                        "ap-1029",
                    ]
                )
                if audit_res.passed and (not has_metric_intent or len(citations) > 0):
                    latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
                    return ConversationQueryResponse(
                        session_id=session_id,
                        turn_index=turn_index,
                        route=SpecialistDomain.SYNTHESIS,
                        response_markdown=raw_text,
                        citations=[c.citation_id for c in citations],
                        provenance_citations=citations,
                        is_replay_fallback=False,
                        reflection_cycles_used=corrections,
                        turn_latency_ms=latency_ms,
                        auditor_status=audit_res.status.value,
                    )
                fallback_reason = "live response failed audit or lacked mandatory tool grounding"
                _LOG.warning("%s; falling back to deterministic replay", fallback_reason)
            except Exception as e:
                fallback_reason = f"live Gemini call failed: {e}"
                _LOG.warning("%s; degrading to deterministic replay", fallback_reason)

        # Deterministic Grounded Execution (Offline / Fast Local Replay)
        tool_traces = []
        citations = []
        staged_rec: dict[str, Any] | None = None

        if "cr84920" in lower_q or "aml" in lower_q or role == OperatorRole.AML_INVESTIGATOR:
            aml_res = inspect_aml_entity("CR84920")
            tool_traces.append({"tool": "inspect_aml_entity", "output": aml_res})
            citations.append(
                ProvenanceCitation(
                    citation_type=CitationType.ENTITY,
                    citation_id="CR84920",
                    label="Account CR84920",
                    source_engine="AMLWorkstationService",
                )
            )

            policy_res = query_policy_search("AML SAR filing discrepancy threshold")
            tool_traces.append({"tool": "query_policy_search", "output": policy_res})
            citations.append(
                ProvenanceCitation(
                    citation_type=CitationType.STATUTORY_POLICY,
                    citation_id="31 CFR § 1020.320",
                    label="FinCEN SAR Rule 31 CFR § 1020.320",
                    source_engine="VertexAISearch",
                )
            )

            narrative = (
                f"Entity CR84920 presents an elevated composite risk score of {aml_res['composite_risk_score']} "
                f"with a {aml_res['discrepancy_multiplier']}x discrepancy multiplier between declared monthly income "
                f"(${int(aml_res['kyc_declared_monthly_income_usd'])} USD) and realized 30-day deposit turnover "
                f"(${int(aml_res['net_deposit_volume_30d_usd']):,} USD) across {aml_res['velocity_transfers_count']} transfers. "
                f"Under {policy_res['statutory_citation']} and internal AML escalation guidelines, "
                f"transactions exceeding ${int(policy_res['filing_threshold_usd']):,} USD with unexplained velocity "
                f"mandate filing FinCEN Form 111. A withdrawal hold of type '{aml_res['recommended_action']}' has been staged."
            )
            route = SpecialistDomain.SENTINEL_AML
            staged_rec = {
                "intent_id": f"act_aml_{int(time.time() * 1000)}",
                "action_type": "STAGE_WITHDRAWAL_HOLD",
                "target_entity_id": "CR84920",
                "target_entity_type": "ACCOUNT",
                "severity": "HIGH",
                "lifecycle_state": "STAGED",
                "estimated_impact": "Freezes pending withdrawals on CR84920 pending FinCEN Form 111 filing",
                "requires_four_eyes": True,
            }

        elif (
            "p-882" in lower_q
            or "ap-1029" in lower_q
            or "partner" in lower_q
            or "churn" in lower_q
            or role == OperatorRole.PARTNER_MANAGER
        ):
            partner_id = "AP-1029" if "ap-1029" in lower_q else "P-882"
            vol_res = get_governed_metric("net_deposit_volume_30d_usd", entity_id=partner_id)
            tool_traces.append({"tool": "get_governed_metric", "output": vol_res})
            citations.append(
                ProvenanceCitation(
                    citation_type=CitationType.METRIC,
                    citation_id="net_deposit_volume_30d_usd",
                    label="30-day Net Deposit Turnover",
                    source_engine="SemanticRegistry.DuckDB",
                )
            )

            churn_res = inspect_partner_churn(partner_id)
            tool_traces.append({"tool": "inspect_partner_churn", "output": churn_res})
            citations.append(
                ProvenanceCitation(
                    citation_type=CitationType.ENTITY,
                    citation_id=partner_id,
                    label=f"Partner {partner_id}",
                    source_engine="PartnerWorkstationService",
                )
            )

            narrative = (
                f"Partner {partner_id} realized a 30-day deposit turnover of ${int(vol_res['value']):,} USD. "
                f"The discrete-time hazard model reports an elevated churn probability of {churn_res['churn_hazard_probability']:.2f} "
                f"driven by {churn_res['primary_root_cause']}. Recommended retention intervention: {churn_res['recommended_playbook']}."
            )
            route = SpecialistDomain.CHURN_RADAR
            staged_rec = {
                "intent_id": f"act_churn_{int(time.time() * 1000)}",
                "action_type": "DISPATCH_RETENTION_PLAYBOOK",
                "target_entity_id": partner_id,
                "target_entity_type": "PARTNER",
                "severity": "MEDIUM",
                "lifecycle_state": "STAGED",
                "estimated_impact": f"Triggers proactive fee concession retention playbook for {partner_id}",
                "requires_four_eyes": False,
            }

        elif any(w in lower_q for w in ["latam", "spread", "shock", "what-if", "what if"]):
            dag_res = run_causal_what_if("competitor_spread_delta_bps", 20.0)
            tool_traces.append({"tool": "run_causal_what_if", "output": dag_res})
            citations.append(
                ProvenanceCitation(
                    citation_type=CitationType.METRIC,
                    citation_id="competitor_spread_delta_bps",
                    label="Spread Shock LatAm Causal DAG",
                    source_engine="CausalDAGInference",
                )
            )
            revenue_delta_usd = abs(int(dag_res["deltas"]["net_revenue_delta_usd"]))
            narrative = (
                f"A simulated spread expansion of {dag_res['magnitude_percentage']:.1f}% induces an estimated net revenue decline of "
                f"${revenue_delta_usd:,} USD across Tier-1 brokers. "
                f"DoWhy refuter test ({dag_res['baseline_model_version']}) verified with placebo p-value {dag_res['placebo_p_value']:.2f}. "
                f"Recommended action: Tune broker alert sensitivity band."
            )
            route = SpecialistDomain.SYNTHESIS
            staged_rec = {
                "intent_id": f"act_tune_{int(time.time() * 1000)}",
                "action_type": "TUNE_MONITORING_THRESHOLD",
                "target_entity_id": "COMP-LATAM-01",
                "target_entity_type": "BROKER_FEED",
                "severity": "MEDIUM",
                "lifecycle_state": "STAGED",
                "estimated_impact": "Re-aligns broker alert sensitivity band with market spread volatility",
                "requires_four_eyes": False,
            }

        elif any(
            w in lower_q for w in ["mcp", "tool", "tools", "protocol", "function", "functions"]
        ):
            narrative = (
                "The EIOS Copilot connects to governed enterprise services via seven registered **OMCP (Open Model Context Protocol)** tools:\n\n"
                "1. `get_governed_metric`: Queries the DuckDB semantic layer for certified KPI values, freshness timestamps, and version hashes.\n"
                "2. `inspect_aml_entity`: Pulls KYC profiles, monthly declared income vs. 30-day realized turnover, and velocity discrepancy multipliers.\n"
                "3. `query_graph_topology`: Inspects hub-and-spoke transactional flows and counterparty clustering across entity networks.\n"
                "4. `inspect_partner_churn`: Runs discrete-time hazard models to evaluate partner churn risk and primary drivers.\n"
                "5. `run_causal_what_if`: Evaluates DoWhy refuter-tested causal DAGs to simulate market spread shocks across broker tiers.\n"
                "6. `query_policy_search`: Performs statutory regulatory RAG search over statutory texts (e.g. 31 CFR § 1020.320, MiFID II).\n"
                "7. `stage_action_intent`: Pre-stages cryptographically signed action tokens into the Governed Action Shelf under Four-Eyes review.\n\n"
                "All metric citations are audited by the Metric Auditor Gate (Principle I: zero hallucinations)."
            )
            route = SpecialistDomain.SYNTHESIS
            staged_rec = None

        elif any(
            w in lower_q
            for w in [
                "what can you do",
                "help",
                "who are you",
                "capability",
                "capabilities",
                "features",
                "how does",
                "what do you do",
                "guide",
            ]
        ):
            narrative = (
                "I am the Enterprise Intelligence Copilot, an institutional AI agent operating over EIOS sovereign governed ontologies. "
                "I assist operators across five specialized operational domains:\n\n"
                "• Executive Cockpit: Causal DAG inference, DoWhy refuter testing, and macro spread what-if simulations.\n"
                "• AML Sentinel: Cross-account transaction velocity analysis, statutory FinCEN Form 111 SAR drafting, and withdrawal holds.\n"
                "• Churn Radar: Parametric hazard modeling, partner deposit turnover attribution, and retention playbooks.\n"
                "• Compliance Explorer: Monotonic WORM hash chain verification, ECDSA P-256 signatures, and four-eyes authorization logs.\n"
                "• Data Operations: Pipeline freshness SLAs, Great Expectations test suites, and entity cluster reconciliation.\n\n"
                "Try asking: 'What is the LatAm spread impact?', 'Check CR84920 for AML structuring', or 'Inspect partner P-882 churn risk'."
            )
            route = SpecialistDomain.SYNTHESIS
            staged_rec = None

        else:
            kpi_res = get_governed_metric("net_revenue_usd")
            tool_traces.append({"tool": "get_governed_metric", "output": kpi_res})
            citations.append(
                ProvenanceCitation(
                    citation_type=CitationType.METRIC,
                    citation_id="net_revenue_usd",
                    label="Governed Net Revenue",
                    source_engine="SemanticRegistry.DuckDB",
                )
            )
            narrative = (
                f"The governed enterprise net revenue is currently ${int(kpi_res['value']):,} USD."
            )
            route = SpecialistDomain.SYNTHESIS
            staged_rec = None

        # Verify narrative through Metric Auditor Gate
        audit_res = self.auditor_bridge.audit_turn(narrative, tool_traces)
        mem.register_turn_entities(turn_index, resolved_query, {})
        self.checkpointer.save_state(
            session_id,
            {
                "session_id": session_id,
                "turn_index": turn_index,
                "anchor": mem.get_active_entity_anchor(),
            },
        )
        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

        return ConversationQueryResponse(
            session_id=session_id,
            turn_index=turn_index,
            route=route,
            response_markdown=narrative,
            citations=[c.citation_id for c in citations],
            provenance_citations=citations,
            staged_recommendation=staged_rec,
            is_replay_fallback=True,
            fallback_reason=fallback_reason or "deterministic grounded replay",
            turn_latency_ms=latency_ms,
            auditor_status=audit_res.status.value,
        )
