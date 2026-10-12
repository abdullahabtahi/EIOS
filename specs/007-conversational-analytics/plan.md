# Implementation Plan: Conversational Analytics & Multi-Agent Reasoning Mesh (F06)

**Branch**: `007-conversational-analytics` | **Date**: 2026-10-07 | **Spec**: [specs/007-conversational-analytics/spec.md](spec.md)

**Input**: Feature specification from `specs/007-conversational-analytics/spec.md`, `specs/007-conversational-analytics/research.md`, `docs/brief/data.md` §4, §5, `docs/models_and_evals.md` §6, and `FEIOS/docs/spikes_and_adrs.md` (ADR-016).

---

## Summary

Deliver the **Conversational Analytics & Multi-Agent Reasoning Mesh** (completing Slice S1 / F06), operationalizing the interactive intelligence tier for the Deriv Enterprise Intelligence Operating System. The architecture implements the **LangGraph Supervisor Pattern** to coordinate specialized domain agents ({`Synthesis`, `SentinelAML`, `ChurnRadar`, `PartnerFraud`}) while bounding deliberation cycles to a maximum of 3 turns to guarantee $p95 < 3.5\text{s}$ turn latency `[TARGET]`. It deploys a **Supervisory Router** achieving $\ge 95\%$ classification accuracy `[TARGET]`, maintains a structured **Evidence Ledger** and rolling session memory across multi-turn drill-downs, enforces honest uncertainty with canonical `"insufficient data"` refusals, scans all output prose through the **Metric Auditor Gate** (0 untraceable numbers `[TARGET]`), and stages non-autonomous recommendation cards via the **Action Execution Sink** with zero direct database write execution.

---

## Technical Context

**Language/Version**: Python 3.14+  
**Primary Dependencies**: `pydantic>=2.13.5`, `fastapi>=0.142.2`, `duckdb>=1.1.0`, `scikit-learn>=1.5.0`, `langgraph>=0.2.0`, `langchain-google-vertexai>=2.0.0`
**Storage**: In-memory `BlackboardState`, session memory stores, DuckDB hot state (`HotStateEngine`), and append-only decision ledger  
**Testing**: `pytest`, `pytest-cov`, `pytest-xdist` with $\ge 80\%$ line and branch coverage gate `[TARGET]`  
**Target Platform**: Linux server / macOS / Cloud Run  
**Performance Goals**:
- Supervisory Router classification latency: $< 50\text{ms}$ (rule-based) / $< 800\text{ms}$ (semantic) `[TARGET]`
- Multi-agent turn turnaround latency: $< 3.5\text{s}$ p95 across deliberation cycles `[TARGET]`
- Maximum reflection cycles per turn: $\le 3$ cycles `[TARGET]`
- Prompt token envelope: $\le 4,000$ tokens per turn (via evidence ledger compaction) `[TARGET]`  
**Constraints**:
- Constitution Principle I: Zero metric hallucination (Metric Auditor Gate firewall) `[TARGET]`
- Constitution Principle II: Zero autonomous writes (KMS-signed draft action proposals only) `[TARGET]`
- Constitution Principle III: Honest refusal on ungrounded/speculative queries (`"insufficient data"`) `[TARGET]`
- Constitution Principle IV: All analytical data consumed strictly via OMCP tools
- Constitution Principle VII: Specialist sub-agents behind Supervisory Router; decoupled pipelines
- Constitution Principle VIII: Deterministic cached replay fallback with `[REPLAY]` badges

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (LLMs Never Compute Metrics)**: PASS. All numerical assertions are backed by `EvidenceItem` records retrieved from deterministic OMCP tools. Prose is scanned by `MetricAuditorGate` prior to client delivery.
- **Principle II (No Autonomous Write-Back)**: PASS. Agents lack execute tools in their allow-lists. Conversational requests for action format non-autonomous `RecommendationCard` proposals staged for human sign-off.
- **Principle III (Honest Uncertainty & Causal Gate)**: PASS. Unanswerable queries lack data products and trigger immediate honest refusal with `"insufficient data"`. Counterfactual explorations qualify causal bounds and emit extrapolation warnings on outlier shocks ($> 3.0\sigma$).
- **Principle IV (Ontology-Only Access)**: PASS. Specialists interact with domain logic exclusively through canonical OMCP tools (`get_metric`, `get_causal_chain`, `run_scenario`, `get_forecast`, `get_partner_signals`, `get_ring_evidence`).
- **Principle V (Provenance & Labelling)**: PASS. All claims cite entity IDs (`account_id`, `partner_id`), data product names, and `as_of` timestamps.
- **Principle VI (Eval-First & Baselines)**: PASS. Router evaluated against the $\ge 95\%$ benchmark target across 10 golden dialogue scenarios in `evals/golden/dialogues/`. Unit-testable code subject to $\ge 80\%$ coverage gate.
- **Principle VII (Decoupled Pipelines & Specialized Agents)**: PASS. Four dedicated specialist agents orchestrated through a centralized Blackboard Coordinator (`ADR-016`), eliminating monolithic God Agents.
- **Principle VIII (Deterministic Fallback)**: PASS. Upstream gateway timeouts or model failures trigger cached replay templates marked with `[REPLAY]` metadata.

---

## Architecture & Component Topology

```text
FEIOS/src/eios/conversation/
├── __init__.py                 # Public package exports
├── models.py                   # Pydantic v2 schemas: RouteDecision, EvidenceItem, ConversationalTurn, BlackboardState
├── graph.py                    # LangGraph StateGraph, ActionExecutionSink, and Supervisor nodes
├── memory.py                   # Sliding-window context compactor & pronominal entity resolver
├── auditor_bridge.py           # MetricAuditorGate egress scanner & replay circuit breaker
├── specialists/
│   ├── __init__.py             # Specialist package exports
│   ├── base.py                 # BaseSpecialistAgent protocol with tool allow-list enforcement
│   ├── synthesis.py            # SynthesisSpecialist: get_causal_chain, run_scenario, get_forecast, get_briefing
│   ├── aml.py                  # SentinelAMLSpecialist: get_entity, traverse_graph, get_ring_evidence
│   ├── churn.py                # ChurnRadarSpecialist: get_partner_signals, search_comms
│   └── fraud.py                # PartnerFraudSpecialist: get_ring_evidence, traverse_graph
└── engine.py                   # ConversationEngine facade orchestrating router, coordinator, and audited stream
```

---

## Project Structure & Deliverables

### Documentation (this feature)
```text
specs/007-conversational-analytics/
├── spec.md                     # Feature specification
├── plan.md                     # This file
├── research.md                 # Technical research & ADR-016 resolution
├── data-model.md               # Pydantic v2 domain models & state lifecycle
├── quickstart.md               # Interactive validation guide & benchmark commands
├── contracts/                  # JSON schema interface contracts
│   ├── conversation-query-request.schema.json
│   ├── conversation-query-response.schema.json
│   └── blackboard-state.schema.json
└── checklists/
    └── requirements.md         # Spec quality checklist
```

### Source Code & Test Layout
```text
FEIOS/
├── src/eios/conversation/      # Implementation modules (models, router, coordinator, memory, engine)
├── tests/conversation/         # Comprehensive test suite:
│   ├── conftest.py             # Seeded conversation fixtures, OMCP server mock, session state
│   ├── test_models.py          # Pydantic v2 schema validation
│   ├── test_supervisory_router.py # Router accuracy tests against golden queries (>= 95% target)
│   ├── test_session_memory.py  # Multi-turn context continuity and pronominal resolution
│   ├── test_counterfactual_turn.py # Assumption challenge & scenario shock propagation
│   ├── test_honest_refusal.py  # Unanswerable query refusal validation ("insufficient data")
│   ├── test_arbitration_cycles.py # Max 3 reflection cycles & statutory compliance precedence
│   ├── test_metric_auditor_chat.py # Metric Auditor Gate egress firewall validation
│   └── test_e2e_conversation.py # Full multi-turn integration test across golden dialogues
└── evals/
    └── registry.yaml           # Register conversation-validation suite
```

---

## Complexity Tracking

> **Constitution Check has zero violations. No unjustified complexity introduced.**

| Component | Justification | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **LangGraph Supervisor Pattern** | Needed to eliminate cyclic agent deadlocks and enforce statutory priority predictably. | Direct peer-to-peer messaging creates $O(N^2)$ message storms, infinite loops, and latency SLA breaches. |
| **Decoupled Evidence Ledger** | Decouples raw JSON tool dumps from natural language context window. | Naive raw JSON message history causes prompt token exhaustion and dropped entity citations. |
| **Metric Auditor Egress Firewall** | Non-negotiable enterprise trust requirement (Principle I). | Relying on prompt instructions alone fails under adversarial or speculative user prompts. |
