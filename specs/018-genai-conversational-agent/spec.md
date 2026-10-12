# Feature Specification: Production-Grade Gen AI Conversational Agent Mesh (F018)

**Feature Branch**: `018-genai-conversational-agent`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Production-grade conversational intelligence agent powered by Google Cloud Vertex AI and Gemini 3.8 Flash, orchestrated via LangGraph hierarchical supervisor with human-in-the-loop governance, dual-engine grounding across Palantir-style 4-fold Ontology (OMCP) and Vertex AI Search/RAG for unstructured regulatory policy retrieval, with full Metric Auditor Gate protection and automated evaluation harness."

---

## Strategic Framing & Enterprise Doctrine

This specification defines the production-grade conversational intelligence layer for the Enterprise Intelligence Operating System (EIOS). The design fuses three institutional doctrines:
1. **QuantumBlack / McKinsey Rewired Agentic Doctrine**: Multi-Agent Shared Blackboard architecture with an Arbitrating Coordinator, bounded deliberation cycles ($\le 3$ reflections), role-specialized agents with tool allow-lists, and continuous decision-learning flywheels.
2. **Palantir Foundry / AIP Ontology Doctrine**: True four-fold Ontology integration (**Data** object/link traversal, **Logic** server-side functions, **Action** 2PC intent tokens with Four-Eyes quorum, and **Security** markings). The LLM is the cognitive interface to the operational ontology, not a standalone chatbot.
3. **Google Cloud Reference Architecture**: Vertex AI **Gemini 3.8 Flash** engine with native **Context Caching** ($75\%$ cost reduction, sub-500ms TTFT), **Vertex AI Search & Vector RAG** (`types.VertexAISearch`, `types.VertexRagStore`), Cloud Run v2 HTTP/2 SSE streaming, Firestore session checkpointing, Cloud KMS P-256 asymmetric signatures, and Vertex AI Gen AI Evaluation.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dual-Engine Grounded Inquiries across Ontology & Regulatory Policies (Priority: P1 - MVP)

An operational cockpit investigator (AML Officer, MLRO, Compliance Head, or Executive) asks natural language questions that require both hard quantitative metrics and qualitative regulatory policy guidance (e.g., *"Does entity CR84920's 16x turnover discrepancy violate our Q3 2026 AML Risk Policy, and does it require an immediate FinCEN Form 111 filing?"* `[BRIEF monitoring.md]`).

The system uses Gemini 3.8 Flash with Automatic Function Calling (AFC) to invoke the dual-engine grounding pipeline:
1. **Structured Ontology (OMCP)**: Resolves deterministic account balances, KYC income declarations, discrepancy multipliers, and syndicate network graphs via `SemanticRegistry.DuckDB` and `AMLWorkstationService`.
2. **Unstructured Knowledge (Vertex AI Search & RAG Store)**: Retrieves exact passages from the indexed AML Escalation Policy, 31 CFR § 1020, and historical SAR precedent cases.
3. **Metric Auditor Gate**: Verifies all numerical values against the tool execution trace, exempts normalized statutory citations, and streams a verified narrative with 100% provenance citations.

**Why this priority**: Solves the core enterprise pain point: investigators currently waste hours cross-referencing static policy PDFs and disparate database dashboards. Delivers instant, auditable synthesis.

**Independent Test**: Submit a prompt requiring both metric calculation and regulatory rule lookups. Verify that the agent calls both OMCP and Vertex AI Search tools, passes through the Metric Auditor Gate with zero ungrounded numbers, cites both data timestamps and policy section numbers, and completes within $p95 < 3.5\text{s}$.

**Acceptance Scenarios**:
1. **Given** an active AML investigation into `#CR84920`, **When** the investigator asks *"What is their realized turnover versus declared income, and what filing threshold applies?"*, **Then** the agent calls `inspect_aml_entity("CR84920")` and `query_policy_search("SAR filing discrepancy threshold")`, returns the verified $16.0\times$ multiplier and $\$8,000$ volume, cites `31 CFR § 1020.320`, and passes the Metric Auditor Gate with `auditor_status: PASS`.
2. **Given** an ungrounded or speculative question (e.g. *"Estimate how much total illicit crypto will flow through unmonitored competitors next year?"*), **When** evaluated by the supervisor, **Then** the agent invokes Principle III and returns the canonical refusal `"insufficient data"` with zero hallucinated figures.

---

### User Story 2 - Multi-Turn Conversational Investigation with LangGraph Session Memory (Priority: P2)

An executive or partner manager conducts a multi-turn diagnostic dialogue drilling into decaying partners or spread anomalies without repeating prior context (e.g., Turn 1: *"Which LatAm partners experienced login decay following rival spread cuts?"* $\to$ Turn 2: *"What is AP-1029's churn hazard?"* $\to$ Turn 3: *"What retention playbook does our LatAm VIP policy recommend for them?"* `[BRIEF churn]`).

The system maintains conversational state in a durable Firestore checkpointer (`FirestoreSaver`), preserves active entity anchors (`current_entity: AP-1029`), resolves pronouns (*"them"*, *"their"*), and updates the Cockpit's shared blackboard across sequential turns while adhering to the latency budget ($p95 < 3.5\text{s}$).

**Why this priority**: C-suite executives and senior managers investigate iteratively; requiring them to restate entity IDs or background constraints destroys executive usability.

**Independent Test**: Execute a 5-turn conversational session where Turn 3 references entities and numbers established in Turn 1 and Turn 2. Verify that thread state is preserved across container restarts via Firestore, pronouns resolve accurately, and cumulative provenance citations remain unbroken.

**Acceptance Scenarios**:
1. **Given** Turn 1 identified Partner `AP-1029` as having an $84.0\%$ churn hazard, **When** the operator asks in Turn 2 *"What is their primary root cause?"*, **Then** the agent resolves *"their"* to `AP-1029`, calls `inspect_partner_churn("AP-1029")`, and returns the decay diagnostics without asking the user to re-specify the partner ID.
2. **Given** an active session, **When** the operator refreshes the browser or reconnects to the Cockpit Command Bar, **Then** the conversation history and entity anchors are rehydrated from Firestore within $< 200\text{ms}$.

---

### User Story 3 - Human-in-the-Loop Governed Action Staging (`interrupt` & 2PC Tokens) (Priority: P2)

During an interactive investigation, the operator requests or approves an operational intervention (e.g., *"Hold the pending withdrawal for account CR84920"* or *"Deploy VIP Spread Rebate Playbook for partner AP-1029"* `[BRIEF monitoring.md, churn]`).

Rather than executing a direct database mutation, the LangGraph workflow triggers a Human-in-the-Loop breakpoint using `langgraph.types.interrupt`:
1. The agent calls `stage_action_intent` to emit a structured `ActionIntentToken` (specifying type, target entity, parameters, evidence references, and requesting agent ID).
2. The token is cryptographically signed using Google Cloud KMS (ECDSA P-256) and stamped with a 15-minute expiration timer and single-use nonce.
3. The staged action card appears in the Cockpit Governed Action Shelf.
4. Execution halts until an authorized second officer provides Four-Eyes authorization. Zero autonomous write-back occurs.

**Why this priority**: Irreversible financial and regulatory mutations (freezing client funds, clawing back affiliate commissions) carry massive legal liabilities and strictly enforce Constitution Principle II.

**Independent Test**: Prompt the agent to *"Freeze account CR84920 immediately"*. Assert that no SQL `UPDATE/DELETE` is executed, the agent emits an `ActionIntentToken` with KMS signature, the turn returns a staged recommendation card, and the state pauses awaiting Four-Eyes approval.

**Acceptance Scenarios**:
1. **Given** an investigator prompt to hold a withdrawal, **When** processed, **Then** the system returns a staged `RecommendationCard` with `status: "STAGED_FOR_REVIEW"`, an ECDSA P-256 signed `ActionIntentToken`, and an explicit notification that a second officer must authorize the action.
2. **Given** an attempt by an agent or user to execute an action without a valid second-eye token, **When** submitted to `/api/cockpit/actions/authorize`, **Then** the endpoint rejects the commit with HTTP 400 (`Four-Eyes Violation: Authorizing officer cannot match initiator`).

---

### User Story 4 - Multi-Agent Supervisory Arbitration with Bounded Reflection (Priority: P3)

In complex cross-domain scenarios, different domain specialists hold conflicting propositions (e.g., the Partner Retention Agent proposes a $\$15,000$ VIP commission rebate to retain Partner `AP-1029`, while the Partner Fraud Sentinel flags `AP-1029`'s sub-affiliate `SUB-101` for mirror trading collusion `[BRIEF fraud, churn]`).

The LangGraph `SupervisorRouter` coordinates deliberation across specialized agents via a shared Blackboard state:
1. Routes sub-goals to `PartnerRetentionSpecialist` and `PartnerFraudSpecialist`.
2. Reconciles conflicting findings using the Compliance Priority Hierarchy (Fraud/AML holds supersede commercial retention playbooks).
3. Bounds the reflection loop to a maximum of 3 cycles ($\le 3$) to guarantee turn latency limits ($p95 < 3.5\text{s}$) and prevent multi-agent oscillation.

**Why this priority**: Enterprise intelligence platforms fail when siloed bots recommend counter-productive actions in isolation. The supervisory router delivers holistic executive alignment.

**Independent Test**: Simulate an inquiry on an entity with simultaneous churn risk and fraud alerts. Verify that the supervisor detects the conflict, prioritizes compliance over commercial retention, limits reflection cycles to $\le 3$, and presents a consolidated trade-off card.

**Acceptance Scenarios**:
1. **Given** a partner with both a high churn score and an active mirror-trading alert, **When** queried by the operator, **Then** the supervisor synthesizes both domains, prioritizes the fraud investigation, blocks automated commercial rebates, and explains the trade-off.
2. **Given** an agent deliberation reaching 3 reflection cycles without consensus, **When** cycle 3 completes, **Then** the supervisor forces a `FINISH` state, outputs the best-effort evidence, and flags the conflict for human review.

---

### User Story 5 - Automated Evaluation Harness & Red-Line Gates (Priority: P3)

The platform engineering and MLOps teams require continuous automated verification that model updates, prompt edits, and ontology changes do not introduce numerical hallucinations, safety violations, or latency regressions before deployment to staging or production.

The system executes an automated evaluation harness leveraging Vertex AI `EvalTask` and EIOS Red-Line test suites:
1. Computes **Faithfulness** and **Groundedness** metrics against synthetic golden sets.
2. Runs blocking Red-Line gates RL-1 through RL-7 in CI.
3. Records all test runs, token usages, and auditor pass rates to the evaluation store.

**Why this priority**: Protects against model degradation and provides the empirical evidence pack required for enterprise governance and portfolio credibility.

**Independent Test**: Execute the evaluation harness against 100 test cases containing clean queries, adversarial prompt injections, and planted ungrounded numbers. Verify that 100% of ungrounded cases are caught by the Metric Auditor Gate, faithfulness scores exceed $0.95$, and CI blocks on any violation.

**Acceptance Scenarios**:
1. **Given** a test dataset of 50 grounded turns, **When** evaluated via Vertex AI `EvalTask`, **Then** the average Groundedness score is $\ge 0.95$ and Metric Auditor Gate pass rate is $100.0\%$.
2. **Given** an adversarial test case attempting to inject an ungrounded revenue calculation, **When** evaluated, **Then** the Metric Auditor Gate blocks the turn with `auditor_status: BLOCKED` and records the unanchored token.

---

## Edge Cases

- **Vertex AI Outage or Network Partition**: If the Vertex AI API is unreachable or times out ($> 5\text{s}$), the system must degrade immediately to Constitution Principle VIII (Deterministic Fallback), serving precomputed cached briefing cards with an explicit `[REPLAY]` fallback badge.
- **Extreme Extrapolation in What-If Shocks**: When a user inputs a counterfactual shock exceeding $3.0\sigma$ (e.g. $+800\%$ spread shift), the agent must execute the SCM but inject an explicit warning that non-linear boundary extrapolation risks high variance.
- **Conflicting Statutory Citations**: When a narrative cites multiple regulatory jurisdictions (e.g. FinCEN vs. MAS vs. FCA), the legal citation normalizer must parse section codes accurately to prevent false-positive auditor blocks.
- **Large Graph Hub Explosion**: In entities connected to central payment gateways or CGNAT IP addresses ($k > 100$), the graph traversal tool must dynamically collapse the supernode into a cluster badge, preventing context window exhaustion.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Model & Infrastructure
- **FR-001**: The system MUST utilize Google Cloud Vertex AI's `gemini-3.8-flash` model via the official `google-genai` Python SDK.
- **FR-002**: The system MUST support configurable model aliasing via environment variable `EIOS_GEMINI_MODEL` with validated fallback to `gemini-2.5-flash` in supported Vertex AI regions.
- **FR-003**: The system MUST implement Vertex AI **Context Caching** (`client.caches.create()`) for system instructions, domain ontologies, and OMCP tool schemas to maintain sub-500ms TTFT.
- **FR-004**: System prompts MUST be version-controlled, immutable, and referenced by cryptographic hash IDs.

#### Multi-Agent Orchestration & Memory
- **FR-005**: The agent mesh MUST be structured as a LangGraph Hierarchical Supervisor pattern with an Arbitrating Coordinator and specialized domain agents.
- **FR-006**: Specialized agents MUST include `ExecutiveSynthesisAgent`, `AMLInvestigatorAgent`, `PartnerRetentionAgent`, `PartnerFraudAgent`, and `GovernanceComplianceAgent`.
- **FR-007**: Each specialized agent MUST have a strict tool allow-list; cross-domain tool execution must be routed through the supervisor.
- **FR-008**: Multi-agent deliberation MUST be bounded to a strict maximum of 3 reflection cycles per turn.
- **FR-009**: Conversational state, message history, entity anchors, and hypothesis blackboards MUST be persisted per thread using a durable checkpointer (Firestore / SQLite).
- **FR-010**: Pronominal references (*"them"*, *"their"*, *"it"*) MUST be resolved to the active entity anchor from the session memory.

#### Tool Execution & Dual-Engine Grounding
- **FR-011**: The system MUST implement an OMCP (Ontology Model Context Protocol) tool registry exposing all analytical engines to Gemini via Automatic Function Calling (AFC).
- **FR-012**: `get_governed_metric` MUST resolve metrics strictly from the Semantic Metric Registry (`DuckDB`) with definition version, as-of timestamp, and steward role.
- **FR-013**: `inspect_aml_entity` MUST retrieve KYC declarations, discrepancy multipliers, composite risk scores, and syndicate ring sizes from `AMLWorkstationService`.
- **FR-014**: `query_graph_topology` MUST execute multi-hop graph traversal with dynamic hub suppression for node degrees $k > 100$.
- **FR-015**: `inspect_partner_churn` MUST return discrete-time hazard probabilities, CUSUM change-point diagnostics, and sub-affiliate referral networks.
- **FR-016**: `run_causal_what_if` MUST execute parametric shock propagation over DoWhy refuter-verified DAGs with $95\%$ confidence bounds.
- **FR-017**: The system MUST integrate unstructured knowledge retrieval using `types.VertexAISearch` for regulatory compliance rulebooks (FinCEN, FATF, SEC).
- **FR-018**: The system MUST integrate vector similarity retrieval using `types.VertexRagStore` for past SAR precedents and partner communication transcripts.

#### Governance & Metric Auditor Gate
- **FR-019**: Every quantitative scalar emitted in agent narratives MUST be verified by `MetricAuditorGate` against the turn's tool execution trace within $\pm 1\%$ tolerance.
- **FR-020**: Narratives containing unanchored business metrics MUST be blocked with an explicit `auditor_status: BLOCKED` verdict.
- **FR-021**: Statutory, regulatory, and legal section codes (e.g. `31 CFR § 1020.320`, `Form 111`) MUST be normalized and exempted from numerical audit checks.
- **FR-022**: Operational interventions MUST be staged using `langgraph.types.interrupt`, emitting an `ActionIntentToken` with a Cloud KMS ECDSA P-256 asymmetric signature.
- **FR-023**: No tool or agent path in code may execute a direct database mutation; all write-backs must route through the simulated write-back sink after Four-Eyes authorization.
- **FR-024**: Speculative queries regarding unobservable or future private data MUST return the canonical refusal string `"insufficient data"`.

#### Cockpit Integration & Streaming
- **FR-025**: The presentation gateway MUST stream agent narratives and tool event badges over Server-Sent Events (SSE) via HTTP/2.
- **FR-026**: The Cockpit Command Bar UI MUST render live token streams, provenance citation popovers, tool execution badges, and interactive staged action cards.
- **FR-027**: Operators MUST be able to stage action cards directly to the Governed Action Shelf from conversational recommendations.

---

### Key Entities

- **ConversationSession**: Represents an active operator session, encapsulating `session_id`, `operator_role`, `active_entity_anchor`, `thread_id`, and `created_at`.
- **BlackboardState**: Shared LangGraph state containing message sequences, active hypotheses, tool execution traces, reflection cycle counters, and staged action proposals.
- **ToolExecutionTrace**: Audit record of an OMCP or Vertex AI Search invocation, capturing tool name, input arguments, raw output payload, execution latency, and source engine.
- **ActionIntentToken**: Cryptographically signed proposal for an operational mutation, including `intent_id`, `action_type`, target entity, parameters, KMS key ID, signature, nonce, and 15-minute expiration timestamp.
- **AuditorVerdict**: Output of the Metric Auditor Gate, including boolean `passed`, lists of verified numerical anchors, list of unanchored tokens, and relative tolerance threshold.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **Zero Metric Hallucination (Blocking)**: $100.0\%$ of numerical figures in agent responses match tool execution outputs within $\pm 1\%$ relative tolerance across all test suites. Zero tolerance for unanchored numbers.
- **SC-002**: **Citation Coverage**: $100.0\%$ of substantive assertions cite a valid entity ID, metric ID, or regulatory section reference.
- **SC-003**: **Turn Latency SLA**: Time-to-First-Token (TTFT) is $\le 1.5\text{s}$ at p95; complete turn latency including multi-agent reflection and tool execution is $\le 3.5\text{s}$ at p95.
- **SC-004**: **Supervisor Routing Accuracy**: The supervisory router correctly routes domain-specific queries to the appropriate specialist with $\ge 95.0\%$ accuracy on gold-standard evaluation sets.
- **SC-005**: **Groundedness & Faithfulness**: Achieves an average score of $\ge 0.95$ on Vertex AI `EvalTask` groundedness and faithfulness evaluations.
- **SC-006**: **Statutory Exemption Precision**: Zero false-positive Metric Auditor blocks on compliant legal citations (e.g. `31 CFR § 1020.320`, `314(b)`) across AML SAR test sets.
- **SC-007**: **Zero Autonomous Mutations**: 100% of mutation attempts generate staged `ActionIntentToken` proposals; static and runtime checks verify 0 direct write executions.
- **SC-008**: **Context Cache Cost Efficiency**: Vertex AI Context Caching reduces input token billing by $\ge 70\%$ compared to uncached baseline executions across multi-turn sessions.

---

## Assumptions & Dependencies

- **Assumption 1**: The active Google Cloud Project (`spatial-cat-489006-a4`) has Application Default Credentials (ADC) configured and Vertex AI API (`aiplatform.googleapis.com`) enabled.
- **Assumption 2**: In environments without active GCP network connectivity or during local offline testing, the system operates in Deterministic Offline Replay mode (Constitution Principle VIII), using local fixture caches and verified benchmark traces.
- **Dependency 1**: Requires `google-genai>=0.1.0` and `langgraph>=0.2.0` Python packages.
- **Dependency 2**: Requires in-process `DuckDB` Semantic Metric Registry for sub-5ms quantitative KPI queries.
- **Dependency 3**: Cloud KMS key ring `governance` for ECDSA P-256 digital signing.
