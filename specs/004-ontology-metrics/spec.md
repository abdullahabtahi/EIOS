# Feature Specification: Layer 2 Kinetic Ontology & Semantic Metric Layer (F03)

**Feature Branch**: `004-ontology-metrics`  
**Created**: 2026-10-05  
**Status**: Draft  
**Input**: User description: "F03-ontology-metrics: Layer 2 Kinetic Ontology & Semantic Metric Layer. Scope per initial_plan.md §3.2–§4, docs/foundry.md, docs/data_products_and_omcp.md, and docs/engagement_plan.md. Provides the four-fold integration of Data, Logic, Action, and Security. Implements Governed Metric Registry (ADR-003) over hot-state DuckDB with sub-10ms query execution; Kinetic Ontology core modeling 13 Object Types, 9 Link Types, and 7 Action Types; NetworkX in-memory Property Graph with Hub Suppression (ADR-004, ADR-008); Deterministic Functions on Objects; Metric Auditor Gate (Constitution Principle I, Red-Line RL-1); and Governed Action Intent Hub emitting Cloud KMS ECDSA P-256 signed single-use nonces (Constitution Principle II) exposed via OMCP tool surface (read and propose only, zero direct write-back)."

**Constitution references**:
- **Principle I: LLMs Never Compute Business Metrics** (Every quantitative value shown to a user or used in a decision MUST come from a deterministic tool call through the Governed Metric Registry or an Ontology Function; Metric Auditor Gate blocks any output containing unanchored figures, enforcing Red-Line test RL-1).
- **Principle II: No Autonomous Write-Back (NON-NEGOTIABLE)** (Agents have read and propose tools only; no agent-callable execute tool exists. Every mutation is an Action Intent signed with Cloud KMS ECDSA P-256, single-use, nonce-bound, expiring, and approved by an authenticated human with four-eyes policy for High severity).
- **Principle IV: Data as a Product, Ontology-Only Access** (Agents and cockpit consume data products exclusively through the Ontology API / OMCP tool surface, never raw tables. Security markings `PII`, `SENSITIVE_COMPLIANCE`, `PARTNER_COMMERCIAL` are filtered server-side, and PII pseudonymization is preserved).
- **Principle V: Provenance and Labelling** (`[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]` tags applied to all numbers, metrics, and thresholds).
- **Principle VI: Eval-First, Baselines and Anti-Circularity** (Red-first test suite, $\ge 80\%$ test coverage gate, Red-Line RL-1 verification against adversarial prompts).
- **Principle VII: Specialised Agents and Decoupled Pipelines** (Deterministic metric queries and graph operations are decoupled from LLM inference, serving as typed tools for downstream specialized reasoning agents).
- **Principle VIII: Deterministic Fallback and Operability** (Sub-1.5s NetworkX property graph rehydration on container cold boot, sub-10ms metric queries, native scale-to-zero serverless operation).

**Labelling regime**: figures in this document carry the tags defined in Constitution Principle V and `initial_plan.md` §0.2. `[BRIEF]` anchors to client requirements in `docs/brief/*`. `[ILLUSTRATIVE]` marks generated noise, scenarios, or unanchored values. `[TARGET]` marks an acceptance threshold we commit to measuring. `[ASSUMPTION]` marks an engagement default that a later phase may revise. `[SPIKE]` marks unverified technical claims.

---

## Users of the Platform

- **Executive & Business Stakeholders (CFO, Head of Partnerships, COO)**: Queries real-time business KPIs (churn rates, net deposit velocity, commission volumes, conversion rates) with mathematical certainty, zero hallucination, and full metric lineage.
- **AML / Financial Crime Investigator & MLRO**: Traverses client-account-device networks, inspects suspicious clusters, isolates entity ego-graphs without contamination from shared office/NAT IPs, and reviews proposed `HoldWithdrawal` or `FreezeAccount` action intents.
- **Partner Integrity / Anti-Fraud Analyst**: Evaluates partner referral hierarchies, analyzes mirror-trading and commission recycling rings, inspects multi-tier attribution trees, and proposes `ClawbackCommission` or `SuspendPartner` action intents.
- **Autonomous AI Agents (Supervisory Router, Domain Specialists)**: Interacts with enterprise data and operational systems strictly through typed OMCP tools (`get_metric`, `get_entity`, `traverse_graph`, `propose_action`), never querying raw SQL tables or executing mutations directly.
- **Forward Deployed Engineer (FDE) & Platform Operator**: Governs the metric catalog, defines object schemas and links, monitors graph query latency (p95 $\le 25\text{ms}$), and audits action intent verification logs.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Governed Semantic Metric Registry (Priority: P1)

Enterprise decision-makers and AI agents query standardized operational and financial metrics without risk of conflicting definitions or hallucinated values. The Metric Registry maintains versioned metric definitions (formula, grain, dimensional filters, owner role, unit, and freshness SLA) and executes vectorized aggregations directly against the hot-state columnar store in under 10ms (ADR-003).

**Why this priority**: Implements Constitution Principle I ("LLMs Never Compute Business Metrics"). Without a deterministic metric registry, downstream reasoning agents invent numbers or generate conflicting SQL queries across different turns.

**Independent Test**: Register 10 canonical enterprise metrics (e.g. `ftd_count_28d`, `net_deposit_volume_usd`, `partner_churn_rate`, `active_trader_count`, `average_spread_usd`). Execute 500 concurrent metric queries with variable date filters and dimension slicers against 100,000 records. Assert that all 500 queries return mathematically exact results with formula version metadata in $< 10\text{ms}$ `[TARGET]`.

**Acceptance Scenarios**:

1. **Given** a registered metric definition `net_deposit_volume_usd` with grain `[region, currency]`, **When** an agent calls `get_metric(metric_id="net_deposit_volume_usd", filters={"region": "LATAM"}, period="last_7d")`, **Then** the registry returns the deterministic scalar value, currency unit `USD`, definition version `1.0.0`, timestamp `as_of`, and query execution duration $\le 10\text{ms}$ `[TARGET]`.
2. **Given** a request for an unknown or deprecated metric ID, **When** queried through the registry, **Then** the registry returns a typed `MetricNotFoundError` with a list of available active metrics and matching candidate suggestions, rather than executing arbitrary SQL or returning empty nulls.
3. **Given** a metric definition update (e.g. shifting churn inactivity threshold from 30 days to 28 days), **When** a new definition version `2.0.0` is registered, **Then** historical queries with `definition_version="1.0.0"` remain reproducible while unversioned queries resolve to the active `2.0.0` specification with audit logging.
4. **Given** 100,000 rows in hot state, **When** 50 concurrent metric aggregation queries execute across multiple threads, **Then** 95th percentile query latency is $\le 10\text{ms}$ and CPU utilization remains linear `[TARGET]`.

---

### User Story 2 - Kinetic Ontology Core & Polymorphic Interfaces (Priority: P1)

The platform models enterprise realities as an interconnected object graph representing Data, Logic, Action, and Security (`docs/foundry.md`). It implements 13 Object Types (`ClientAccount`, `Device`, `IPAddress`, `PaymentMethod`, `Partner`, `SubAffiliate`, `Competitor`, `Product`, `Region`, `Case`, `Alert`, `Decision`, `MacroEvent`) and 9 Link Types (`USES_DEVICE`, `CONNECTS_FROM`, `FUNDS_VIA`, `REFERRED_BY`, `SUB_OF`, `COMPETES_IN`, `AFFECTS`, `RAISED`, `DECIDED`). Furthermore, polymorphic interfaces allow consistent interactions across shared entity shapes (such as `TransactingEntity` for both `ClientAccount` and `Partner`).

**Why this priority**: The Ontology is the enterprise operating system's ground truth. It translates raw ingested tables into structured operational semantics required for cross-domain synthesis and multi-hop reasoning.

**Independent Test**: Instantiate instances of all 13 Object Types populated from hot-state tables, link them across the 9 Link Types, and verify that navigating bidirectional relationships (e.g. `ClientAccount` $\rightarrow$ `Device` $\rightarrow$ other `ClientAccount`s) maintains referential integrity, schema typing, and interface polymorphism.

**Acceptance Scenarios**:

1. **Given** hot-state tabular data for a client, **When** converted into an Ontology object, **Then** it produces a strongly-typed `ClientAccount` instance containing unique primary key `client_id`, properties, security markings (`PII`), and typed link accessors.
2. **Given** an existing `ClientAccount` and `Device`, **When** linked via `USES_DEVICE`, **Then** the relationship records cardinality (many-to-many), link metadata (first seen, last seen, session count), and allows bidirectional navigation (`client.devices` and `device.clients`).
3. **Given** an entity implementing the `TransactingEntity` interface, **When** passed to a generic balance or transaction-volume function, **Then** the function executes polymorphically regardless of whether the underlying object is a `ClientAccount` or `Partner`.
4. **Given** an invalid property value or link cardinality violation during object instantiation, **When** validated by the Ontology engine, **Then** the operation fails with a typed `OntologySchemaViolationError` and details the offending constraint.

---

### User Story 3 - In-Memory Property Graph with Hub Suppression (Priority: P1)

Financial crime, bonus abuse, and partner syndicates operate across interconnected networks of accounts, devices, and payment methods. The platform maintains an in-memory property graph (NetworkX) synchronized with hot state. To prevent false merges caused by carrier-grade NATs, shared corporate offices, or family tablets, the graph engine enforces **Hub Suppression** (ADR-004, ADR-008): any context node (e.g. `IPAddress` or `Device`) connected to $\ge 5$ distinct identities is marked with `is_shared_context=True` and pruned during automated ring traversals unless explicitly requested.

**Why this priority**: Required by Palantir FDE doctrine and red-team findings #12 & #17. Unsuppressed graphs explode exponentially into supernodes, falsely accusing innocent families or university campuses of operating multi-million dollar fraud rings.

**Independent Test**: Construct a graph with 200 nodes including 5 distinct fraud rings (cliques of size 3–6) and 2 hub nodes (one campus Wi-Fi IP with degree 25, one family tablet with degree 6). Execute community detection and ego-graph traversals with hub suppression enabled. Assert that the 5 fraud rings are correctly isolated, the hub nodes are tagged `is_shared_context=True`, and false-positive ring merges drop to $\le 0.1\%$ `[TARGET]`.

**Acceptance Scenarios**:

1. **Given** a seed `ClientAccount` ID, **When** `traverse_graph(seed_ids=[...], hops=2, suppress_hubs=True)` is called, **Then** the engine returns all connected entities, edge weights, and community identifiers within $\le 25\text{ms}$ `[TARGET]`.
2. **Given** an `IPAddress` or `Device` with degree $\ge 5$ across distinct KYC identities `[BRIEF]`, **When** the graph engine evaluates topology, **Then** the node is flagged with `is_shared_context=True` and excluded from automated transitive closure clustering.
3. **Given** a container cold boot or rehydration event, **When** reconstructing the property graph from hot state (50,000 nodes, 150,000 edges), **Then** full graph initialization and hub indexing completes in $< 1.5\text{s}$ `[TARGET]`.
4. **Given** an investigator inspecting a known syndicate, **When** they call `traverse_graph(suppress_hubs=False)`, **Then** the engine returns the complete unfiltered graph topology, explicitly decorating hub nodes with high-degree visual badges and warning metadata.

---

### User Story 4 - Deterministic Functions on Objects (Priority: P1)

Complex enterprise metrics and decision logic cannot be expressed as simple SQL sums. The platform provides a suite of server-side deterministic Python functions registered in the Ontology: `partner_value_at_risk`, `ring_membership`, `client_quality_score`, `churn_priority`, and `scenario_propagate`. These functions accept Ontology objects or object sets, execute verified deterministic algorithms, and return typed results. Downstream AI agents call these functions via OMCP; they are strictly forbidden from reimplementing business logic in LLM prompts.

**Why this priority**: Business calculations like Value-at-Risk, churn hazard, and syndicate scoring must be mathematically consistent across human analysts, automated alerts, and AI copilots.

**Independent Test**: Execute each registered ontology function with identical object sets across 100 iterations. Assert 100% deterministic reproducibility, zero floating-point drift, and sub-5ms per-object computation latency.

**Acceptance Scenarios**:

1. **Given** a `Partner` object with historical referral and commission data, **When** `partner_value_at_risk(partner)` is executed, **Then** it calculates expected 90-day commission loss weighted by disengagement hazard with documented parameter coefficients.
2. **Given** a sub-graph of accounts and devices, **When** `ring_membership(cluster)` is executed, **Then** it outputs a deterministic ring severity score $[0.0, 1.0]$, member counts, and suspicious symmetry indicators.
3. **Given** a `ClientAccount` object, **When** `client_quality_score(client)` is executed, **Then** it outputs a composite rating based on tenure, deposit-to-withdrawal ratio, turnover rate, and chargeback history.
4. **Given** invalid or missing object properties required by a function, **When** the function executes, **Then** it raises a typed `OntologyFunctionError` specifying the missing property requirements rather than defaulting to zero or hallucinated assumptions.

---

### User Story 5 - Metric Auditor Gate (Priority: P1)

Downstream LLMs must never present unanchored or hallucinated quantitative values to enterprise users (Constitution Principle I, Red-Line RL-1). The Metric Auditor Gate acts as a mandatory egress firewall intercepting all agent narrative responses. It parses all numeric claims (integers, floats, percentages, dollar amounts, multipliers) from the generated text and matches them against the execution trace of deterministic tool outputs (`get_metric`, `traverse_graph`, ontology functions). If any number cannot be mathematically anchored to a tool output within a narrow formatting tolerance, the gate BLOCKS the response and returns a validation error or repair directive.

**Why this priority**: Hallucinated numbers destroy executive trust faster than any other failure mode. Enforcing RL-1 in CI and at runtime guarantees mathematical veracity.

**Independent Test**: Pass 50 agent responses through the Auditor Gate: 25 compliant responses (where every number matches tool execution outputs) and 25 adversarial responses containing unanchored figures (e.g. invented churn rates, altered dollar values, hallucinated account counts). Assert that 100% of compliant responses pass and 100% of unanchored responses are blocked (0% false acceptance rate) `[TARGET]`.

**Acceptance Scenarios**:

1. **Given** an agent response stating "Partner 8821 generated $142,500 in commission across 38 clients", **When** the execution trace contains tool outputs `{commission: 142500, clients: 38}`, **Then** the Auditor Gate verifies numeric provenance and returns `audit_passed=True`.
2. **Given** an agent response stating "Churn probability increased by 34.2%", **When** no tool output in the trace contains the figure `34.2` (or within rounding tolerance), **Then** the Auditor Gate flags the unanchored figure, returns `audit_passed=False`, lists `untraceable_numbers: ["34.2%"]`, and blocks egress.
3. **Given** formatted numeric expressions (e.g. "$1.4M", "1,400,000", "1400k", "14%"), **When** audited against raw numeric tool outputs, **Then** the parser normalizes numerical representations without false rejections of legitimate rounding.
4. **Given** an unanswerable query with no available tool data, **When** the agent replies "insufficient data to calculate metric", **Then** the Auditor Gate verifies zero unanchored claims and permits the honest uncertainty output.

---

### User Story 6 - Governed Action Intent Hub (Priority: P1)

Autonomous agents must NEVER directly mutate production state or trigger external financial transfers (Constitution Principle II). The platform exposes a strictly governed Action Intent Hub. Agents can only call `propose_action(action_type, parameters, evidence_refs)`. The hub validates parameters against Action Type schemas, calculates severity (Low, Medium, High), attaches cryptographic nonces and short expiration windows (15 minutes), and signs the intent using Cloud KMS ECDSA P-256. Actions remain in `PENDING` state until approved by an authenticated human operator (requiring four-eyes verification for High severity).

**Why this priority**: Principle II is non-negotiable. Operational actions (freezing accounts, clawing back commissions, filing SAR drafts) carry severe legal and commercial consequences.

**Independent Test**: Attempt to invoke mutations without human approval; verify that no execute tool exists in the ontology. Generate 50 Action Intents via `propose_action`, verify their ECDSA P-256 digital signatures, assert replay protection on expired nonces, and enforce four-eyes approval logic on High-severity actions.

**Acceptance Scenarios**:

1. **Given** a high-confidence fraud case, **When** an agent calls `propose_action(action_type="FreezeAccount", params={"client_id": "C-9912", "reason_code": "MIRROR_TRADING"}, evidence_refs=["EVID-101"])`, **Then** the hub generates an `ActionIntentToken` with status `PENDING`, severity `HIGH`, 15-minute expiry `[ASSUMPTION]`, and a valid ECDSA P-256 signature.
2. **Given** a proposed `ActionIntentToken`, **When** inspected by an agent or user, **Then** no direct execution API exists in the tool surface; only human approver endpoints can transition status to `APPROVED`.
3. **Given** a High-severity action (`FreezeAccount`, `ClawbackCommission`, `SuspendPartner`), **When** submitted for approval, **Then** the hub requires two distinct authenticated approver signatures (four-eyes principle) before emitting to the write-back sink.
4. **Given** an expired token ($> 15\text{ min}$) or a reused nonce, **When** presented for approval, **Then** the hub rejects the action with `TokenExpiredError` or `NonceReplayDetectedError`.

---

### User Story 7 - OMCP Tool Surface & Security Marking Enforcement (Priority: P1)

The platform exposes all ontology objects, metrics, graphs, and action proposals via the Model Context Protocol (OMCP) tool interface (`docs/data_products_and_omcp.md`). The OMCP gateway enforces server-side security markings (`PII`, `SENSITIVE_COMPLIANCE`, `PARTNER_COMMERCIAL`). Sensitive properties are filtered based on caller role before payload serialization; PII fields are never returned in plaintext to LLM callers, preserving irreversible token vault pseudonymization.

**Why this priority**: Required by Constitution Principle IV ("Data as a Product, Ontology-Only Access"). Governed security markings prevent confidential compliance investigations or partner commercial terms from leaking across persona boundaries or into untrusted model contexts.

**Independent Test**: Call OMCP tools across three distinct security roles (`PartnerManager`, `AMLInvestigator`, `PublicAgent`). Assert that `AMLInvestigator` can access `SENSITIVE_COMPLIANCE` cases but receives pseudonymized PII, while `PartnerManager` is blocked from compliance cases, and `PublicAgent` receives strictly filtered public metadata.

**Acceptance Scenarios**:

1. **Given** an OMCP request to `get_entity(type="ClientAccount", id="C-1001")` by an AI agent, **When** the entity contains Marking `P` (PII), **Then** all PII attributes (tax ID, phone, email, full name) are returned strictly as vault pseudonymized tokens (`tok_...`), never raw plaintext.
2. **Given** an OMCP request to `get_entity(type="Case", id="CASE-402")` by a caller lacking the `SENSITIVE_COMPLIANCE` marking, **When** evaluated server-side, **Then** the gateway denies access with `InsufficientMarkingError`.
3. **Given** an OMCP tool call to `list_metrics()` or `get_metric()`, **When** the response is constructed, **Then** it includes standard metadata headers: `as_of`, `source_product`, `entity_ids`, `metric_version`, and `execution_duration_ms`.
4. **Given** any OMCP tool invocation, **When** input parameters are supplied, **Then** they are strictly validated against JSON Schema definitions; invalid types or unexpected fields return structured HTTP/MCP client errors.

---

## Edge Cases

- **Extreme Supernodes (Carrier NAT / University Campus)**: An IP address connected to $> 1,000$ accounts could consume excessive memory during graph operations. The system must hard-cap degree traversals and immediately flag the node as `is_shared_context=True` without exploring all edges.
- **Cold-Boot Graph Rehydration During Concurrent Metric Reads**: When a new container instance starts, metric queries against DuckDB hot state must execute immediately without waiting for graph index construction to finish in background memory.
- **Auditor Gate Numerical Formatting Ambiguity**: An agent might write "$1.5M", "1,500,000", "1.50 million", or "1.5 × 10^6". The Auditor Gate normalizer must handle currency symbols, magnitude suffixes (k, M, B), and percentage scales (0.15 vs 15%) without false rejections.
- **Token Signature Replay & Key Rotation**: During Cloud KMS key rotation, active Action Intent Tokens signed with version $N$ must verify successfully until expiration, while new tokens are signed with version $N+1$. Expired tokens must be purged from memory.
- **Transitive Marking Propagation**: When traversing links from a public `Product` to a restricted `Case`, security markings must not be bypassed via relational joins; marking filters must apply at the node level during graph serialization.
- **Disconnected Graph Subgraphs & Island Nodes**: Graph queries on isolated nodes or empty queries must return valid empty payloads without raising unhandled NetworkX exceptions.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Governed Metric Registry (ADR-003)
- **FR-001**: System MUST maintain a declarative Metric Registry cataloging metric definitions with unique `metric_id`, name, mathematical formula, grain, dimension attributes, owner role, unit, and freshness SLA.
- **FR-002**: System MUST execute metric calculations directly against the hot-state columnar store in under $10\text{ms}$ p95 `[TARGET]`.
- **FR-003**: System MUST support historical metric definition versioning (`semantic_version`), ensuring reproducible analytics when definitions evolve.
- **FR-004**: System MUST reject ad-hoc, unregistered metric calculation requests from agents, requiring all figures to originate from registered metrics or ontology functions.
- **FR-005**: Metric queries MUST return standard audit metadata including `as_of`, `metric_version`, `grain`, and `execution_duration_ms`.

#### Kinetic Ontology Core & Interfaces
- **FR-006**: System MUST model the 13 canonical Object Types: `ClientAccount`, `Device`, `IPAddress`, `PaymentMethod`, `Partner`, `SubAffiliate`, `Competitor`, `Product`, `Region`, `Case`, `Alert`, `Decision`, `MacroEvent`.
- **FR-007**: System MUST enforce primary key uniqueness and typed property schemas for all Object Types.
- **FR-008**: System MUST model the 9 canonical Link Types with explicit cardinalities and foreign key mappings: `USES_DEVICE`, `CONNECTS_FROM`, `FUNDS_VIA`, `REFERRED_BY`, `SUB_OF`, `COMPETES_IN`, `AFFECTS`, `RAISED`, `DECIDED`.
- **FR-009**: System MUST support polymorphic Interfaces (e.g. `TransactingEntity` implemented by `ClientAccount` and `Partner`), enabling consistent interactions across shared entity capabilities.
- **FR-010**: System MUST support object-backed links with relationship metadata (e.g. `first_seen`, `last_seen`, `session_count`, `attribution_layer`).

#### In-Memory Property Graph & Hub Suppression (ADR-004, ADR-008)
- **FR-011**: System MUST maintain an in-memory property graph (NetworkX) synchronized with hot-state data.
- **FR-012**: System MUST implement automated Hub Suppression: any context node (`Device` or `IPAddress`) connected to $\ge 5$ distinct identities `[BRIEF]` MUST be flagged with `is_shared_context=True`.
- **FR-013**: Graph traversal operations (`traverse_graph`) MUST prune hub nodes by default when `suppress_hubs=True` is specified.
- **FR-014**: System MUST support multi-hop ego-graph extraction (up to 3 hops) and community detection (Louvain / connected components) with p95 latency $\le 25\text{ms}$ for clusters up to 1,000 nodes `[TARGET]`.
- **FR-015**: System MUST rehydrate the complete in-memory property graph from hot state in $< 1.5\text{s}$ on cold boot `[TARGET]`.

#### Deterministic Functions on Objects
- **FR-016**: System MUST provide server-side deterministic implementations of canonical ontology functions: `partner_value_at_risk`, `ring_membership`, `client_quality_score`, `churn_priority`, and `scenario_propagate`.
- **FR-017**: All ontology functions MUST be pure, stateless, unit-tested, and execute in $\le 5\text{ms}$ per object evaluation `[TARGET]`.
- **FR-018**: AI agents MUST NOT reimplement business function calculations in prompts; functions MUST be invoked via OMCP tool calls.

#### Metric Auditor Gate (Principle I, Red-Line RL-1)
- **FR-019**: System MUST implement a Metric Auditor Gate intercepting all agent narrative outputs before delivery to users or API clients.
- **FR-020**: Auditor Gate MUST extract all numeric tokens (integers, floats, percentages, currency amounts) from agent text via deterministic regex and entity parsing.
- **FR-021**: Auditor Gate MUST verify that every extracted numeric token matches a value produced by a tool execution in the session trace within a configurable rounding tolerance ($\le 1.0\%$).
- **FR-022**: If an unanchored number is detected, Auditor Gate MUST block egress, flag the violation in audit logs, and return an audit rejection payload with `untraceable_numbers`.
- **FR-023**: In CI test suites, Red-Line test RL-1 MUST verify that Auditor Gate intercepts 100% of injected unanchored numbers without regressions `[TARGET]`.

#### Governed Action Intent Hub (Principle II)
- **FR-024**: System MUST expose a propose-only action interface (`propose_action`) for 7 canonical Action Types: `FreezeAccount`, `HoldWithdrawal`, `ClawbackCommission`, `SuspendPartner`, `LaunchRetentionPlaybook`, `EscalateToMLRO`, `FileSARDraft`.
- **FR-025**: System MUST NOT expose any autonomous execute tool to agents or public API endpoints.
- **FR-026**: Action Intent Hub MUST generate cryptographic `ActionIntentToken`s containing parameters, severity level, single-use nonce, and expiration timestamp (15 minutes `[ASSUMPTION]`).
- **FR-027**: Action Intent Hub MUST sign all intent tokens using Cloud KMS ECDSA P-256 for non-repudiation.
- **FR-028**: System MUST enforce a four-eyes approval policy (two distinct authenticated human approvers) for all High-severity actions before write-back simulation.

#### OMCP Tool Surface & Security Markings (Principle IV)
- **FR-029**: System MUST expose the 13 canonical OMCP tools defined in `docs/data_products_and_omcp.md`: `get_metric`, `list_metrics`, `get_entity`, `traverse_graph`, `get_partner_signals`, `get_ring_evidence`, `get_causal_chain`, `run_scenario`, `get_forecast`, `get_briefing`, `search_comms`, `propose_action`, `get_intent_status`.
- **FR-030**: System MUST enforce server-side security markings: `PII` (pseudonymized before model access), `SENSITIVE_COMPLIANCE` (restricted to compliance roles), `PARTNER_COMMERCIAL` (restricted to commercial roles).
- **FR-031**: OMCP tools MUST validate all incoming parameters against JSON Schema contracts and return typed responses with standard metadata headers.

---

### Key Entities *(include if feature involves data)*

- **MetricDefinition**: Governed KPI definition. Attributes: `metric_id`, `name`, `formula`, `grain`, `dimension_filters`, `owner_role`, `unit`, `semantic_version`, `freshness_sla`.
- **OntologyObjectType**: Schema definition for enterprise entities. Attributes: `type_name`, `primary_key`, `properties` (dict of name to type), `interfaces`, `security_markings`.
- **OntologyLinkType**: Relationship definition between object types. Attributes: `link_name`, `source_type`, `target_type`, `cardinality` (1:1, 1:N, N:M), `foreign_key`, `is_object_backed`.
- **PropertyGraphNode**: In-memory graph vertex. Attributes: `node_id`, `node_type`, `degree`, `is_shared_context`, `properties`.
- **PropertyGraphEdge**: In-memory graph edge. Attributes: `source_id`, `target_id`, `edge_type`, `weight`, `metadata`.
- **ActionIntentToken**: Cryptographically signed mutation proposal. Attributes: `intent_id`, `action_type`, `parameters`, `evidence_refs`, `severity`, `status` (`PENDING`, `APPROVED`, `REJECTED`, `EXECUTED`), `nonce`, `issued_at`, `expires_at`, `kms_key_id`, `signature`.
- **AuditVerificationRecord**: Egress audit verification result. Attributes: `trace_id`, `audit_passed`, `extracted_numbers`, `anchored_numbers`, `untraceable_numbers`, `timestamp`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **Metric Query Latency**: 95% of metric queries against the Governed Metric Registry return in under $10\text{ms}$ when evaluated against 100,000 hot-state records `[TARGET]`.
- **SC-002**: **Auditor Gate Verification**: 100% of unanchored or hallucinated numeric claims are intercepted and blocked by the Metric Auditor Gate (0% false acceptance rate on adversarial test suites) `[TARGET]`.
- **SC-003**: **Zero Autonomous Write-Back**: 0% of agent tool invocations directly mutate core state; 100% of mutations require signed Action Intent Tokens and human approval `[TARGET]`.
- **SC-004**: **Cold-Boot Graph Rehydration**: Complete NetworkX in-memory property graph rehydration (50,000 nodes, 150,000 edges) completes in under $1.5\text{s}$ during cold-boot warm-start `[TARGET]`.
- **SC-005**: **Graph Query Latency**: Multi-hop graph traversals (up to 2 hops with hub suppression) return within $25\text{ms}$ p95 `[TARGET]`.
- **SC-006**: **Hub Suppression Accuracy**: Carrier-grade NATs and shared devices ($\ge 5$ identities) achieve $\le 0.1\%$ false-merge rate on entity clusters `[TARGET]`.
- **SC-007**: **Security Marking Leak Prevention**: 100% of PII attributes are delivered as pseudonymized tokens to LLM tool callers; 0% plaintext leaks across all OMCP tool surfaces `[TARGET]`.
- **SC-008**: **Test Coverage Gate**: The complete Layer 2 codebase achieves $\ge 80\%$ line and branch test coverage, with all Red-Line tests passing in CI `[TARGET]`.

---

## Assumptions

- **In-Memory Scale**: For the portfolio POC/production demonstration, hot state and property graphs fit within container memory ($\le 2\text{GB}$ RAM for 100,000 records and 50,000 graph nodes). Production scale-up to billions of edges would leverage Spanner Graph or Neo4j (documented in ADR-004).
- **KMS Emulation / Mock**: In local test and development environments, Cloud KMS ECDSA P-256 signing is backed by an in-memory cryptography key pair simulating Cloud KMS interfaces without requiring live GCP credentials.
- **Token Expiration**: Action Intent Tokens expire after 15 minutes `[ASSUMPTION]`, after which they cannot be approved or executed.
- **Auditor Gate Rounding Tolerance**: A default numerical tolerance of $\pm 1.0\%$ is applied to account for standard float-to-string rounding (e.g. 14.28% vs 14.3%).
- **OMCP Transport**: OMCP tools are accessible both in-process (direct Python function calls for local agent workflows) and via FastMCP/HTTP JSON-RPC for external agent frameworks.
