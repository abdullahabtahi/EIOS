# Implementation Plan: Production-Grade Gen AI Conversational Agent Mesh (F018)

**Branch**: `018-genai-conversational-agent` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/018-genai-conversational-agent/spec.md`

---

## Summary

Build an institutional-grade, multi-agent conversational reasoning mesh powered by Google Cloud Vertex AI's **Gemini 3.8 Flash** engine, orchestrated using a **LangGraph Hierarchical Supervisor**, grounded in the 4-fold **Palantir-style Ontology (OMCP)** and **Vertex AI Search/RAG Store**, and safeguarded by the **Metric Auditor Gate** egress firewall (Constitution Principle I) and **Human-in-the-Loop Two-Phase Commit Action Staging** (Constitution Principle II).

---

## Technical Context

**Language/Version**: Python 3.12+ (Agent Backend) & TypeScript 5.8+ / Next.js 16 (Cockpit Frontend)  
**Primary Dependencies**: `google-genai>=0.1.0`, `langgraph>=0.2.0`, `langchain-core>=0.3.0`, `duckdb>=1.1.0`, `fastapi>=0.115.0`, `pydantic>=2.10.0`  
**Storage**: Google Cloud Firestore (session checkpointing, sequence counters), In-memory DuckDB (hot state), BigQuery (historical lakehouse), Google Cloud Storage (SEC 17a-4 WORM bucket)  
**Testing**: `pytest>=8.0.0`, `pytest-cov>=5.0.0`, `vertexai.evaluation` (EvalTask), Vitest (Cockpit UI)  
**Target Platform**: Google Cloud Platform (Vertex AI, Cloud Run v2, Firestore, Cloud KMS)  
**Project Type**: Multi-agent reasoning mesh & full-stack API integration  
**Performance Goals**: Time-to-First-Token $\le 1.5\text{s}$ at p95; Full turn latency $\le 3.5\text{s}$ at p95; Metric query $< 5\text{ms}$; Context cache hit rate $> 90\%$  
**Constraints**: Zero unanchored numerical figures (Principle I), zero autonomous mutations (Principle II), maximum 3 reflection cycles per turn  
**Scale/Scope**: 5 domain specialist agents, 7 OMCP tools, 14 Layer 1 data product partitions, 2,000 synthetic weekly triage alerts  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Principle | Status | Design Validation |
| :--- | :--- | :--- | :--- |
| **G1** | **I. Zero LLM Metric Math** | **PASS** | Every number originates from OMCP DuckDB tool execution. `MetricAuditorGate` rejects unanchored tokens. |
| **G2** | **II. No Autonomous Write-Back** | **PASS** | `langgraph.types.interrupt` stages `ActionIntentToken` proposals signed with Cloud KMS (ECDSA P-256). Four-Eyes required. |
| **G3** | **III. Honest Uncertainty** | **PASS** | Causal claims validated against DoWhy placebo refuters. Speculative queries return canonical `"insufficient data"`. |
| **G4** | **IV. Ontology-Only Access** | **PASS** | Direct raw SQL access prohibited; all agent interactions route through governed OMCP schemas. |
| **G5** | **V. Provenance and Labelling** | **PASS** | Every claim carries a structured `ProvenanceCitation` referencing entity IDs, metric versions, and policy citations. |
| **G6** | **VI. Eval-First & Red-Line Gates** | **PASS** | Red-Line suite (RL-1 to RL-7) and Vertex AI `EvalTask` block CI promotion. |
| **G7** | **VII. Specialized Agents & Bounded Reflection** | **PASS** | LangGraph Hierarchical Supervisor manages 5 specialists. Deliberation hard-capped at $\le 3$ reflection loops. |
| **G8** | **VIII. Deterministic Fallback** | **PASS** | Vertex AI outages gracefully degrade to cached replay cards stamped with an explicit `[REPLAY]` badge. |

**Result**: 100% PASS on all constitutional gates.

---

## Project Structure

### Documentation (this feature)

```text
specs/018-genai-conversational-agent/
├── spec.md                     # Feature specification (v1, 27 FRs, 8 SCs)
├── plan.md                     # This implementation plan
├── research.md                 # Phase 0 architectural & SDK decisions
├── data-model.md               # Phase 1 Pydantic v2 domain schemas
├── quickstart.md               # Phase 1 developer runnable validation scenarios
├── checklists/
│   └── requirements.md         # Passed quality checklist (100% PASS)
├── contracts/
│   ├── omcp-tool-catalog.schema.json
│   └── conversation-query-response.schema.json
└── tasks.md                    # Created by /speckit-tasks (Phase 2)
```

### Source Code (repository root)

```text
FEIOS/
├── src/eios/
│   ├── conversation/
│   │   ├── __init__.py
│   │   ├── copilot_engine.py      # Core Gemini 3.8 Flash agent & chat session loop
│   │   ├── supervisor.py          # LangGraph Hierarchical Supervisor & StateGraph
│   │   ├── tools.py               # 7 OMCP tools with Automatic Function Calling
│   │   ├── memory.py              # FirestoreSaver persistent checkpointer
│   │   ├── auditor_bridge.py      # MetricAuditorGate egress firewall & legal normalizer
│   │   └── specialists/
│   │       ├── synthesis.py       # Executive Causal SCM specialist
│   │       ├── aml.py             # AML forensic dossier specialist
│   │       ├── churn.py           # Partner hazard & retention specialist
│   │       ├── fraud.py           # Partner fraud & mirror trading specialist
│   │       └── governance.py      # WORM ledger & Four-Eyes compliance specialist
│   ├── cockpit/
│   │   └── server.py              # FastAPI gateway exposing /api/cockpit/copilot/query
│   └── evals/
│       ├── run_vertex_eval.py     # Vertex AI EvalTask groundedness & faithfulness runner
│       └── red_line_runner.py     # Blocking CI runner for RL-1 through RL-7
├── tests/
│   └── conversation/
│       ├── test_copilot_engine.py
│       ├── test_supervisor.py
│       ├── test_omcp_tools.py
│       ├── test_auditor_bridge.py
│       └── test_red_line_gates.py
└── web-prototype/
    └── src/
        ├── app/api/cockpit/copilot/query/route.ts
        └── components/cockpit/shell/copilot-command-bar.tsx
```

---

## Complexity Tracking

No constitutional violations exist; all gates pass 100%. The Complexity Tracking table is not required.
