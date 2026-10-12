# Phase 0 Research: Production-Grade Gen AI Conversational Agent Mesh (F018)

**Feature Branch**: `018-genai-conversational-agent`  
**Date**: 2026-10-10  
**Status**: Completed  
**Domain**: QuantumBlack Multi-Agent Mesh × Palantir AIP Ontology × Google Cloud Vertex AI Architecture  

---

## Decision Matrix & Architectural Research

### 1. Model Engine & Vertex AI SDK Architecture

- **Context**: The conversational agent requires fast multi-turn responses ($p95 < 3.5\text{s}$), high-precision Automatic Function Calling (AFC), and native enterprise grounding.
- **Alternatives Considered**:
  - *Option A*: LangChain OpenAI / Anthropic wrapper via LiteLLM.
  - *Option B*: Legacy `langchain-google-vertexai` wrapper.
  - *Option C (Chosen)*: Unified Google GenAI Python SDK (`google-genai`) with Vertex AI regional endpoints (`spatial-cat-489006-a4` in `us-central1`), targeting `gemini-3.8-flash` with dynamic fallback to `gemini-2.5-flash`.
- **Rationale**:
  - Native support for Vertex AI **Context Caching** (`client.caches.create()`), enabling sub-500ms Time-To-First-Token (TTFT) and $75\%$ reduction in input token costs.
  - Native dual-engine retrieval integration (`types.VertexAISearch` and `types.VertexRagStore`).
  - Automatic Function Calling (AFC) executing strongly typed Python functions without external JSON-RPC marshaling bottlenecks.

---

### 2. Multi-Agent Topology: Hierarchical Supervisor with Bounded Reflection

- **Context**: Siloed single-prompt agents fail when cross-domain constraints collide (e.g. Partner Retention proposing commercial commission rebates while AML Sentinel flags transaction round-tripping). Monolithic "God Agents" violate Constitution Principle VII and hallucinate tool parameters.
- **Alternatives Considered**:
  - *Option A*: Autonomous agent swarm with peer-to-peer handoffs. Rejected because peer-to-peer swarms can oscillate indefinitely and cannot guarantee latency SLOs.
  - *Option B (Chosen)*: **LangGraph Hierarchical Supervisor Pattern** with an Arbitrating Coordinator and 5 domain specialists (`ExecutiveSynthesis`, `AMLInvestigator`, `PartnerRetention`, `PartnerFraud`, `GovernanceCompliance`).
- **Rationale**:
  - Bounded deliberation: A hard constraint of **$\le 3$ reflection cycles** guarantees $p95 < 3.5\text{s}$ turn latency.
  - Explicit compliance priority hierarchy: Regulatory and fraud holds strictly supersede commercial retention playbooks.
  - Durable persistence: State graph threads are checkpointed in Google Cloud Firestore (`FirestoreSaver`), surviving container recycles.

---

### 3. Dual-Engine Grounding: 4-Fold Ontology (OMCP) + Vertex AI Search/RAG

- **Context**: An enterprise operating system requires both hard quantitative mathematical truth (account balances, hazard probabilities) and qualitative regulatory guidance (FinCEN SAR rules, SEC 17a-4 mandates, brokerage SOPs).
- **Architecture**:
  ```
  ┌─────────────────────────────────────────────────────────────┐
  │                    GEMINI 3.8 FLASH                         │
  └──────────────┬──────────────────────────────┬───────────────┘
                 │                              │
                 ▼ Structured Math              ▼ Unstructured Policies
  ┌─────────────────────────────┐  ┌────────────────────────────┐
  │ EIOS ONTOLOGY API (OMCP)    │  │ VERTEX AI SEARCH & RAG     │
  │ • SemanticRegistry.DuckDB   │  │ • 31 CFR § 1020 Rulebooks  │
  │ • AMLWorkstationService     │  │ • LatAm VIP Rebate SOPs    │
  │ • Causal SCM & DoWhy Graph  │  │ • Past SAR Precedents      │
  └─────────────────────────────┘  └────────────────────────────┘
  ```
- **Principle I Enforcement**: LLMs never compute business arithmetic. All quantitative scalars are returned by OMCP tools and validated by `MetricAuditorGate`.
- **Statutory Normalization**: Regulatory citations (e.g. `31 CFR § 1020.320`) are parsed and exempted from the numerical auditor to eliminate false-positive rejections on compliance narratives.

---

### 4. Human-in-the-Loop Governance & Two-Phase Commit (2PC)

- **Context**: Autonomous write-back is strictly forbidden by Constitution Principle II. Operational actions (e.g. `HoldWithdrawal`, `ClawbackCommission`, `DeployRetentionPlaybook`) carry irreversible legal and financial consequences.
- **Mechanism**:
  1. When an agent proposes a mutation, LangGraph invokes `langgraph.types.interrupt()`.
  2. The agent calls `stage_action_intent`, creating an `ActionIntentToken`.
  3. The token is cryptographically signed using Google Cloud KMS (ECDSA P-256) and stamped with a 15-minute expiration timer and single-use nonce.
  4. The staged action card is surfaced in the Cockpit Governed Action Shelf.
  5. The action remains in `STAGED_FOR_REVIEW` until an authenticated second officer authorizes it via Four-Eyes dual approval.

---

### 5. Automated SRE & Evaluation Harness

- **Context**: Continuous verification that model, prompt, or ontology updates never introduce hallucinations or degrade precision.
- **Evaluation Pipeline**:
  - **Vertex AI Gen AI Evaluation SDK (`EvalTask`)**: Automated scoring of **Faithfulness** ($\ge 0.95$) and **Groundedness** ($\ge 0.95$).
  - **Red-Line CI Gates (RL-1 to RL-7)**:
    - RL-1: Zero Metric Hallucination (100% tool match, 0 unanchored numbers).
    - RL-2: Zero Autonomous Mutation (Static AST check + runtime deny).
    - RL-3: 100% Citation Coverage (Entity ID + timestamp).
    - RL-4: Honest Refusal ("insufficient data" on speculative queries).
    - RL-5: Statutory Exemption Accuracy (0 false-positive blocks on legal citations).
    - RL-6: Turn Latency SLA ($p95 < 3.5\text{s}$, TTFT $< 1.5\text{s}$).
