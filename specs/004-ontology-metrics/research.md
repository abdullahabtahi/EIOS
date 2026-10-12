# Research & Architecture Decisions: Layer 2 Kinetic Ontology & Semantic Metric Layer (F03)

**Branch**: `004-ontology-metrics` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

---

## 1. Architectural Spike S-02 / ADR-003: Metric Registry Engine

### Problem & Context
Constitution Principle I dictates that **LLMs never compute business metrics**. All numbers shown in reports, briefings, or chat interfaces must originate from deterministic code. Previously, Cube Core was considered as a headless semantic layer. However, Cube requires a Node.js daemon, CubeStore (or Redis) cache, and complex process orchestration that conflicts with Google Cloud Run scale-to-zero container architectures (preventing sub-3s cold boot).

### Options Evaluated
1. **Option A: Cube Core (Headless Semantic Layer Daemon)**
   - *Pros*: Out-of-the-box SQL generation, pre-aggregations, role-based access.
   - *Cons*: Heavy Node.js background process + CubeStore distributed daemon; container image size $> 800\text{MB}$; cold boot $> 6.5\text{s}$; high memory footprint ($\ge 1.2\text{GB}$ baseline); complex multi-container deployment on Cloud Run.
2. **Option B: Native In-Process Python DuckDB Metric Registry (`eios.ontology.metrics`)** *(Selected)*
   - *Pros*: Zero network hops or inter-process IPC; queries execute in-process against `:memory:eios_hot_state` in $\le 5\text{ms}$; minimal container image footprint ($+0\text{MB}$ additional daemons); instant cold-boot readiness; declarative YAML/Python metric definitions with versioning and audit trails.
   - *Cons*: Must maintain custom query compiler for dimensional filters (readily implemented with parametrized DuckDB relational API).

### Decision & Rationale
**Selected Option B: Native In-Process DuckDB Metric Registry**.  
Queries execute in $\le 5\text{ms}$ (well under the $\le 10\text{ms}$ SLA in `SC-001`), cold boot adds $0.0\text{s}$ latency overhead, and scale-to-zero is natively supported. Metric definitions are declarative, versioned (`semantic_version`), and validated with strict schemas.

---

## 2. Architectural Spike S-04 / ADR-004: In-Memory Property Graph & Hub Suppression

### Problem & Context
AML syndicates, bonus abuse rings, and partner fraud operate over multi-hop relationships (Accounts $\leftrightarrow$ Devices $\leftrightarrow$ IPs $\leftrightarrow$ Payment Methods). Using an external graph database (Neo4j, Memgraph, or Spanner Graph) adds external cloud dependencies, network latency, and high infrastructure costs for a serverless engagement. However, naive in-memory graphs suffer from **supernode explosion** (Carrier-grade NATs or shared office IPs connecting to thousands of users, causing false-positive fraud merges).

### Options Evaluated
1. **Option A: External Graph Database (Neo4j / Spanner Graph)**
   - *Pros*: Distributed persistence, native Cypher / GQL support.
   - *Cons*: External managed service cost, VPC connector latency ($15–40\text{ms}$ roundtrip), cold start connection overhead.
2. **Option B: In-Memory NetworkX Property Graph with Degree-Based Hub Suppression** *(Selected)*
   - *Pros*: In-process Python memory; sub-millisecond neighbor lookups; rehydrates from DuckDB hot state in $< 1.5\text{s}$ for 50,000 nodes; supports native NetworkX algorithms (ego-graphs, Louvain community detection).
   - *Cons*: Upper scale ceiling ($\sim 1\text{M}$ nodes per container instance; documented in ADR-004 as transitioning to Spanner Graph in multi-region enterprise scale).

### Decision & Rationale
**Selected Option B: In-Memory NetworkX Property Graph (`eios.ontology.graph`)**.  
To prevent supernode explosion, the graph engine implements **Hub Suppression** (ADR-008): any context node (`IPAddress` or `Device`) connected to $\ge 5$ distinct identities is tagged with `is_shared_context=True`. During automated ring traversals (`suppress_hubs=True`), edges through hub nodes are pruned, capping false merges at $\le 0.1\%$ (`SC-006`).

---

## 3. Metric Auditor Gate Architecture (Constitution Principle I & Red-Line RL-1)

### Problem & Context
Downstream LLM reasoning agents (Executive Synthesis, Churn Radar, AML Sentinel) generate natural language narratives. Non-deterministic generation can easily introduce hallucinated figures, corrupted currency totals, or invented percentages, destroying executive credibility.

### Options Evaluated
1. **Option A: LLM-as-a-Judge / Secondary LLM Verifier**
   - *Pros*: Natural language understanding of paraphrased statistics.
   - *Cons*: Non-deterministic; adds $800–1500\text{ms}$ latency and extra token costs; can itself hallucinate or pass false numbers.
2. **Option B: Deterministic Regex & AST Span Matcher with Numerical Normalization** *(Selected)*
   - *Pros*: 100% deterministic; executes in $< 2\text{ms}$; extracts all numeric tokens (integers, floats, percentages, multipliers, currency symbols) and matches them against tool output values in the call trace with configurable floating-point tolerance ($\le 1.0\%$).
   - *Cons*: Requires robust normalization for suffixes ("$1.2M" $\rightarrow$ 1,200,000, "15%" $\rightarrow$ 0.15).

### Decision & Rationale
**Selected Option B: Deterministic Span Matcher (`eios.ontology.auditor`)**.  
Enforces a non-bypassable egress firewall. If an agent states "churn increased by 34.2%" but no tool in the trace returned 34.2, the response is BLOCKED and an audit failure record is emitted.

---

## 4. Governed Action Intent Hub (Constitution Principle II & Cloud KMS Signing)

### Problem & Context
Constitution Principle II strictly prohibits autonomous write-back. Every mutation must be an Action Intent that is signed, single-use, nonce-bound, expiring, and approved by an authenticated human (four-eyes for High severity).

### Technical Design
- **Action Intent Tokens (`eios.ontology.actions`)**:
  - `intent_id`: UUIDv4.
  - `action_type`: One of 7 canonical types (`FreezeAccount`, `HoldWithdrawal`, `ClawbackCommission`, `SuspendPartner`, `LaunchRetentionPlaybook`, `EscalateToMLRO`, `FileSARDraft`).
  - `parameters`: Strictly validated against Action Type Pydantic schema.
  - `evidence_refs`: Array of entity IDs or citation keys.
  - `severity`: Derived from Action Type (`HIGH` or `MEDIUM`).
  - `nonce`: Cryptographically secure 128-bit random token.
  - `issued_at` / `expires_at`: 15-minute validity window.
  - `signature`: ECDSA P-256 signature using Cloud KMS (emulated in local dev via `cryptography.hazmat.primitives.asymmetric.ec`).
- **Approval Workflow**:
  - `PENDING`: Created by agent via `propose_action`. No execute tool exists in the ontology.
  - `APPROVED`: Transitioned only via human approval endpoint (`POST /v1/ontology/actions/approve`). High severity requires two distinct approver identities (`approver_1`, `approver_2`).
  - `EXECUTED`: Dispatched to simulated write-back sink and logged to append-only Decision Ledger.

---

## 5. Security Markings & OMCP Tool Surface (Constitution Principle IV)

### Problem & Context
The Ontology exposes data to external AI agents via the Model Context Protocol (OMCP). Agents must never access raw tables or un-redacted PII. Furthermore, commercial or compliance data must not leak across persona boundaries.

### Technical Design
- **Security Markings**:
  - `Marking.PII`: Fields containing customer personal identifiable information. Irreversibly pseudonymized using the Layer 1 Token Vault (`tok_client_<hex16>`). Raw PII is never loaded into Ontology objects.
  - `Marking.SENSITIVE_COMPLIANCE`: Cases, SAR drafts, and AML alerts restricted to compliance persona roles (`MLRO`, `AMLInvestigator`).
  - `Marking.PARTNER_COMMERCIAL`: Specific commission rates, margin agreements, and competitor intelligence restricted to `HeadOfPartnerships` and `Executive`.
- **Server-Side Enforcement**:
  - When an OMCP tool (`get_entity`, `traverse_graph`) serializes an object, it inspects the caller's authorization context. If the caller lacks a required marking, marked fields are redacted or the query is rejected with `InsufficientMarkingError`.
