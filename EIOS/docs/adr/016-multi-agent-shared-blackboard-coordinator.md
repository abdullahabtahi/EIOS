# ADR-016: Multi-Agent Shared Blackboard Topology & Arbitrating Coordinator Protocol

## Status

Superseded by ADR-019

## Date

2026-10-05

## Context

The Layer 3 Reasoning Mesh hosts multiple specialist domain agents ({Client, Financial, Partner, Operational, Competitive, Compliance, Sentinel-AML, Synthesis, Scenario, Briefing}).
In complex scenarios (such as an affiliate experiencing sudden referral drops while associated clients trigger AML smurfing alerts), specialist agents may generate conflicting hypotheses or incompatible action proposals (e.g., Partner Lead recommending a VIP retention bonus while Sentinel-AML recommends freezing accounts and clawing back commissions).
Without a structured arbitration topology, direct peer-to-peer agent messaging risks cyclic execution, divergent deliberations, unbounded token consumption, and SLA breaches.

## Options considered

- **Direct Peer-to-Peer Agent Mesh**: Agents call each other directly via RPC/tools. Cons: $O(N^2)$ communication complexity, high risk of deadlock or infinite loops, unpredictable turn latency.
- **Hierarchical Supervisory Router Only**: Simple static intent router that forwards query to a single agent. Cons: Cannot synthesize multi-domain investigations or arbitrate conflicting recommendations across multiple specialist agents.
- **Shared Blackboard Topology with Arbitrating Coordinator Agent (Chosen)**: All shared context, evidence, and intermediate hypotheses reside on a centrally managed state Blackboard (LangGraph State). An Arbitrating Coordinator Agent orchestrates investigation rounds, routes sub-goals to domain specialists, halts redundant investigations, detects conflicts, and arbitrates high-priority compliance interventions over commercial retention playbooks.

## Decision

Adopt the **Shared Blackboard Topology with an Arbitrating Coordinator Agent** for Layer 3:
1. **Shared Blackboard State**: Contains user query, active domain hypotheses, accumulated OMCP tool evidence, proposed action candidates, and deliberation history.
2. **Conflict Resolution Hierarchy**: Statutory compliance and financial crime interventions (AML/Fraud) strictly take precedence over commercial optimization actions (Retention/Bonus).
3. **Bounded Deliberation Cycles**: A hard termination cap of **at most 3 reflection/handoff cycles** is enforced by the Coordinator, guaranteeing execution SLA ($< 3.5\text{s}$ p95 turn latency).

## Consequences

- Positive: Eliminates infinite agent oscillation and guarantees turnaround SLAs.
- Positive: Clear, explainable multi-agent audit trail recorded in session memory.
- Positive: Governed priority hierarchy guarantees compliance mandates always supersede growth goals.
- Negative: Requires formal schema definition for the blackboard state and Coordinator prompts.

## Evidence

Architectural review by enterprise FDE team; red-team analysis of multi-agent cyclic deadlocks in financial workflows.

## Revisit when

Autonomous multi-party negotiation across external institutional agents is required.

## Supersession

The coordinator and blackboard were never built; the LangGraph mesh stayed a keyword-routed stub. ADR-019 replaces it with one ADK agent per workstation over the governed tool port, and the mesh was deleted on 2026-10-14.
