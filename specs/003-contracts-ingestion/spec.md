# Feature Specification: Layer 1 Ingestion Spine & Contract Gateway (F02)

**Feature Branch**: `003-contracts-ingestion`  
**Created**: 2026-10-04  
**Status**: Draft  
**Input**: User description: "F02-contracts-ingestion: Layer 1 Ingestion Spine & Contract Gateway. Scope per initial_plan.md §3.3, §8 (slice S0), docs/data_products_and_omcp.md, and docs/engagement_plan.md. Ingests data streams via Pub/Sub and webhooks, enforces Pydantic contracts for all 14 data products, routes breaches to DLQ with zero silent dropping, hydrates in-memory DuckDB hot state via sub-3s Parquet warm-start (ADR-012), resolves client identities via hybrid deterministic and probabilistic record linkage with hub suppression (ADR-008), enforces PII pseudonymization (Marking P), and exposes real-time DQ/freshness SLA monitoring."

**Constitution references**:
- Principle I: LLMs Never Compute Business Metrics (Layer 1 provides deterministic, validated hot state and scalar measurements).
- Principle II: No Autonomous Write-Back (DLQ and audit trails are append-only; mutation intents are strictly governed).
- Principle IV: Data as a Product, Ontology-Only Access (All 14 domain datasets have enforced contracts; violations route to DLQ + raise alerts + mark product `DEGRADED`; zero silent dropping; PII fields pseudonymized under Marking P).
- Principle V: Provenance and Labelling (`[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]` tags applied to all numbers).
- Principle VI: Eval-First, Baselines and Anti-Circularity (Red-first test suite, $\ge 80\%$ coverage, evaluated against seeded test vectors).
- Principle VII: Specialised Agents and Decoupled Pipelines (Streaming ingestion is strictly decoupled from batch training and SCM fitting, ADR-013).
- Principle VIII: Deterministic Fallback and Operability (Sub-3.0s Parquet warm-start rehydration on container cold boot, ADR-012).

**Labelling regime**: figures in this document carry the tags defined in Constitution Principle V and `initial_plan.md` §0.2. `[BRIEF]` anchors to client requirements in `docs/brief/*`. `[ILLUSTRATIVE]` marks generated noise, scenarios, or unanchored values. `[TARGET]` marks an acceptance threshold we commit to measuring. `[ASSUMPTION]` marks an engagement default that a later phase may revise. `[SPIKE]` marks unverified technical claims.

---

## Users of the Platform

- **Data Engineer**: Operates the ingestion pipeline, monitors contract compliance across all 14 data products, inspects dead-letter queues, and investigates schema breaches.
- **Platform SRE / Operator**: Monitors ingestion latency, container cold-boot warm-start duration, Pub/Sub flow control, and data freshness SLOs (p95 $\le 30\text{s}$).
- **Fraud Analyst & Compliance Officer (MLRO)**: Relies on the Single Client View (SCV) to link suspect accounts across MT5, Deriv Trader, and DP2P without false merges from shared family devices or office IPs.
- **Data Protection Officer (DPO)**: Verifies that PII fields (Marking P) are irreversibly pseudonymized before landing in hot analytical state or exposing to downstream reasoning agents.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-Time Multi-Modal Event Ingestion (Priority: P1)

The platform ingests continuous real-time streams of financial trades, cashier deposits/withdrawals, partner click logs, and platform telemetry. Ingestion must support both asynchronous pull-based messaging (simulating Cloud Pub/Sub) and synchronous push-based webhooks (HTTP API). Ingestion buffers incoming events into micro-batches without blocking on downstream analytical processes or model training (ADR-013).

**Why this priority**: Without a working ingestion spine, no live operational data reaches the hot state or ontology layer.

**Independent Test**: Send 1,000 trade events through the push webhook and 1,000 transaction events through the asynchronous subscriber. Assert that all 2,000 events are acknowledged, micro-batched, and accessible in the staging pipeline within target latency.

**Acceptance Scenarios**:

1. **Given** an operational ingestion service, **When** a valid trade execution or deposit event is posted to the webhook endpoint (`/v1/events/ingest`), **Then** the service returns HTTP 202 Accepted with a unique event receipt ID in $\le 50\text{ms}$ `[TARGET]`.
2. **Given** an active Pub/Sub subscription, **When** messages arrive on the topic, **Then** the background subscriber processes the micro-batch, applies flow control (max 1,000 messages or 10 MB per pull), and acknowledges (`ack()`) successful messages.
3. **Given** a transient system error during ingestion processing, **When** processing fails unexpectedly, **Then** the message is explicitly rejected (`nack()`) or deferred to allow redelivery without message loss.
4. **Given** concurrent event streams across all 14 data products, **When** sustained ingestion occurs, **Then** throughput scales to $\ge 500\text{ events/sec}$ per container instance without unbounded memory growth `[TARGET]`.

---

### User Story 2 - Contract Validation Gate & Zero-Drop DLQ Circuit Breaker (Priority: P1)

Every incoming event is evaluated against its respective Data Product Contract (enforcing Pydantic schemas, required fields, null-rate ceilings, value range boundaries, and volumetric anomaly limits). If an event breaches contract rules (e.g. injected by Layer 0 `BreachInjector`), it is NEVER silently dropped. Instead, it is immediately diverted to the Dead-Letter Queue (`eios.l1.dlq.v1`), logged as a structured warning event, and causes the parent data product status to toggle to `DEGRADED` (triggering an operational freshness banner).

**Why this priority**: Principle IV and Constitution Rule 4 dictate that invalid data must never contaminate the analytical hot state, and silent dropping of operational telemetry is strictly forbidden.

**Independent Test**: Feed 500 valid records and 50 malformed records (null required fields, negative deposit amounts, schema type errors). Assert that 500 records pass into hot state, exactly 50 records land in the DLQ with structured error reasons, and the product status is flagged as `DEGRADED`.

**Acceptance Scenarios**:

1. **Given** an incoming event payload, **When** it strictly matches the data product's Pydantic schema, **Then** the event is validated and passed to the hot-state buffer.
2. **Given** a payload containing missing required fields, type mismatches, or null rate violations, **When** validated by the contract gate, **Then** the event is rejected from hot state and appended to the DLQ with error codes and field paths.
3. **Given** a contract breach event, **When** routing to the DLQ, **Then** a structured Cloud Logging event is emitted containing `{event_type: "CONTRACT_BREACH", product_name: "...", breach_reasons: [...]}`.
4. **Given** a data product experiencing contract breach rates $> 0.05\%$ `[TARGET]`, **When** the breach threshold is crossed, **Then** the product health status immediately transitions from `HEALTHY` to `DEGRADED`, exposing an operational alert flag for the Common Operational Picture.

---

### User Story 3 - In-Memory Hot-State Engine with Parquet Warm-Start Rehydration (Priority: P1)

The platform maintains an in-memory columnar hot state (DuckDB named database `:memory:eios_hot_state`) representing the sliding operational window (last 24 hours to 30 days depending on data product). On container startup or cold boot, the engine rehydrates historical baselines directly from columnar Parquet lakehouse snapshots in $< 3.0\text{s}$ for $\ge 100,000$ baseline records (ADR-012). The hot state supports sub-millisecond vectorized queries for metrics, anomaly detection, and graph extraction.

**Why this priority**: Serverless scale-to-zero containers wipe in-memory state. Without rapid warm-start rehydration, cold starts render the operational digital twin blind for minutes (red-team finding #11).

**Independent Test**: Measure the exact elapsed wall-clock time required to initialize `:memory:eios_hot_state` from 100,000 records of synthetic Parquet files on cold start. Execute concurrent analytical SQL queries across multiple reader threads and assert zero corruption or race conditions.

**Acceptance Scenarios**:

1. **Given** a fresh container initialization, **When** the FastAPI application lifespan startup executes, **Then** `:memory:eios_hot_state` rehydrates the 14 data product baseline tables from local or cloud Parquet partitions within $< 3.0\text{s}$ `[TARGET]`.
2. **Given** active real-time events passing contract validation, **When** events arrive, **Then** they are appended to the hot-state tables in vectorized micro-batches without locking reader queries.
3. **Given** concurrent analytical metric queries, **When** executed against hot-state tables, **Then** query latency p95 is $\le 15\text{ms}$ `[TARGET]`.
4. **Given** a readiness health probe check (`/readyz`), **When** warm-start rehydration has successfully completed, **Then** the probe returns HTTP 200 OK; if still rehydrating, it returns HTTP 503 Service Unavailable.

---

### User Story 4 - Single Client View (SCV) Entity Resolution with Hub Suppression (Priority: P1)

Trader activity originates across fragmented systems: Deriv MT5, Deriv Trader WebSockets, Deriv P2P (DP2P), and local Payment Agents. The Entity Resolution Engine links fragmented identities into a canonical Single Client View (`CanonicalClientEntity`). It executes a two-stage hybrid approach: (1) deterministic exact linking on strong keys (tax ID, phone hash, email hash), and (2) probabilistic record linkage (Fellegi-Sunter / Splink) on fuzzy names and device fingerprints. Crucially, it enforces **Hub Suppression**: devices or IP addresses shared by $\ge 5$ distinct identities (such as expatriate family tablets, office networks, or carrier-grade NATs) are tagged with `is_shared_context=True` and prevented from collapsing distinct accounts into false single entities (ADR-008).

**Why this priority**: Required by Palantir SCV doctrine and red-team findings #12 & #17. Without entity resolution, multi-accounting and cross-platform fraud cannot be connected; without hub suppression, thousands of benign users sharing campus or family Wi-Fi are falsely merged.

**Independent Test**: Process a test batch containing 100 distinct traders with multiple fragmented platform IDs, 10 deliberate multi-accounting syndicates, and a 10-person family sharing a single tablet. Assert that fragmented IDs resolve to single canonical IDs, while family members sharing the tablet remain separate entities with `is_shared_context=True`.

**Acceptance Scenarios**:

1. **Given** records across MT5, Deriv Trader, and DP2P sharing exact cryptographic tax ID or normalized phone hashes, **When** entity resolution runs, **Then** they are linked to the same `canonical_client_id` with deterministic confidence 1.0.
2. **Given** records sharing device fingerprints and high name similarity ($\ge 0.88$ Jaro-Winkler), **When** probabilistic linkage executes, **Then** they are linked with computed match weight and match probability $\ge 0.85$.
3. **Given** a shared device fingerprint or IP address associated with $\ge 5$ distinct accounts exhibiting differing KYC tax identities (e.g. family or office hard negatives), **When** entity resolution evaluates the cluster, **Then** hub suppression activates: the accounts remain distinct, the link is flagged as `is_shared_context=True`, and the false-merge rate is $\le 0.1\%$ `[TARGET]`.
4. **Given** a canonical client entity resolution update, **When** new linkages are discovered, **Then** the canonical identity mapping in DuckDB is updated with full lineage audit links to the source platform IDs.

---

### User Story 5 - Deterministic PII Pseudonymization Token Vault (Priority: P1)

To comply with global privacy regulations (GDPR/MFSA) and Constitution Principle IV, raw PII fields (client full names, plain emails, phone numbers, tax IDs, and physical addresses) marked under **Marking P** must never be stored in plaintext within the hot analytical state or exposed to LLM reasoning agents. The Token Vault performs deterministic HMAC-SHA256 pseudonymization with salt rotation, producing opaque surrogate tokens (e.g. `tok_client_9f83a1b...`). Reverse mapping back to plaintext is isolated in a restricted vault accessible only via high-privilege auditing workflows.

**Why this priority**: Constitution Principle IV mandates that PII is pseudonymized before any analytical or LLM layer. Storing raw PII in DuckDB or sending it to LLM contexts violates compliance and security gates.

**Independent Test**: Feed raw client records containing realistic names, emails, and tax IDs through the pseudonymization service. Inspect the resulting DuckDB tables and verify zero plaintext PII exists. Verify that tokenization of identical identifiers produces identical tokens (preserving referential integrity) and that reversing a token requires high-privilege credentials.

**Acceptance Scenarios**:

1. **Given** an incoming event containing fields marked as PII (`Marking P`), **When** passing through the gateway, **Then** all PII fields are transformed into deterministic pseudonym tokens prior to hot-state insertion.
2. **Given** identical raw PII values across separate events or data products (e.g. same email in client profile and DP2P transaction), **When** tokenized, **Then** they generate identical surrogate tokens to preserve relational joins and analytical integrity.
3. **Given** hot-state analytical queries or OMCP tool responses, **When** inspected by automated scans, **Then** zero raw email addresses, phone numbers, or unhashed tax IDs are present.
4. **Given** an authorized compliance request requiring plain identity revelation, **When** evaluated against the Token Vault with valid security clearance, **Then** the token is decrypted with full access audit logging.

---

### User Story 6 - Real-Time Data Quality (DQ) & Freshness SLA Monitoring Board (Priority: P2)

Data engineers and SREs need real-time observability into the health of all 14 data products. The Data Quality Board tracks end-to-end freshness lag ($T_{\text{now}} - T_{\text{event}}$), null rate percentages, volume anomaly z-scores, contract breach counters, and entity resolution conflicts. It exposes a standardized API (`/v1/dq/status`) and streams updates to the Common Operational Picture cockpit.

**Why this priority**: SRE operability requirement (Constitution Principle VIII and engagement plan §2). SREs and users must instantly know if an analytical domain is degraded or operating on stale data.

**Independent Test**: Query `/v1/dq/status`. Verify it returns structured health status (`HEALTHY`, `DEGRADED`, `CRITICAL`), p95 freshness lag, total breaches in the last 1 hour, and null-rate counters across all 14 data products.

**Acceptance Scenarios**:

1. **Given** normal operational flow, **When** event latency $T_{\text{now}} - T_{\text{event}}$ is $\le 30\text{s}$ `[TARGET]`, **Then** product freshness status is reported as `HEALTHY`.
2. **Given** an upstream pipeline stall where event lag exceeds the product's freshness SLA (e.g. $> 1\text{ minute}$ for transactions or $> 1\text{ hour}$ for engagement signals), **When** DQ monitoring evaluates the product, **Then** the product status transitions to `DEGRADED` and emits a freshness alert banner.
3. **Given** the `/v1/dq/status` endpoint, **When** invoked by an SRE or dashboard client, **Then** it returns a comprehensive JSON status object for all 14 data products in $\le 25\text{ms}$ `[TARGET]`.
4. **Given** Parquet Lakehouse export batches, **When** written to disk/GCS, **Then** each batch partition is accompanied by an immutable `_lineage.json` metadata record documenting source seed, record counts, and contract schema versions.

---

### Edge Cases

- **Bursty Traffic / DLQ Flooding**: Upstream bug sends 50,000 malformed events per second. The gateway must rate-limit DLQ emissions, apply circuit breaking, and drop to sampling or backpressure rather than crashing with out-of-memory errors.
- **Extreme Graph Hubs**: A corporate proxy, university Wi-Fi, or carrier-grade NAT has 5,000+ distinct accounts active in a single day. Hub suppression must smoothly tag the node without attempting an $O(N^2)$ pairwise comparison that freezes the container.
- **Corrupted / Empty Parquet Snapshot**: On container cold boot, a Parquet snapshot file in the storage path is zero-byte or corrupt. The warm-start loader must fall back to the previous good snapshot or initialize an empty hot state while raising an urgent alert.
- **Clock Drift & Future Timestamps**: Events arrive with future timestamps ($T_{\text{event}} > T_{\text{now}} + 5\text{m}$) due to client clock skew. Contract validation must reject or clamp the timestamp to prevent corrupting time-series rolling windows.
- **Unicode & Non-ASCII Ingestion**: Names or comments with emojis, RTL text, or zero-width spaces must be normalized without throwing encoding exceptions or breaking tokenization.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an asynchronous event subscriber supporting Cloud Pub/Sub pull protocols with configurable message and byte flow control.
- **FR-002**: System MUST provide an HTTP push webhook endpoint (`POST /v1/events/ingest`) accepting single events or micro-batches with sub-50ms response times.
- **FR-003**: System MUST enforce strict Pydantic contract validation against all 14 Layer 1 data product schemas defined in `docs/data_products_and_omcp.md`.
- **FR-004**: System MUST reject any payload violating data types, missing required fields, or breaching defined null-rate thresholds.
- **FR-005**: System MUST route 100% of contract-breaching payloads to the Dead-Letter Queue (`eios.l1.dlq.v1`) with full error diagnostics, never silently dropping any record.
- **FR-006**: System MUST emit structured JSON logs for all contract breaches with severity `WARNING` or `ERROR` compatible with Cloud Logging Query Language.
- **FR-007**: System MUST automatically toggle a data product's operational state to `DEGRADED` whenever its breach rate exceeds 0.05% in a rolling 1-hour window.
- **FR-008**: System MUST maintain an in-process, vectorized columnar hot-state database (`:memory:eios_hot_state`) using DuckDB.
- **FR-009**: System MUST implement a warm-start procedure on container startup that rehydrates hot-state tables from Parquet lakehouse snapshots in $< 3.0\text{s}$ for 100,000 records.
- **FR-010**: System MUST expose a container readiness probe (`GET /readyz`) that returns 200 OK only after hot-state warm-start rehydration is complete and all contracts are active.
- **FR-011**: System MUST expose a container liveness probe (`GET /healthz`) that responds with 200 OK while the event loop and background subscriber are responsive.
- **FR-012**: System MUST support concurrent read queries against DuckDB hot state without blocking on streaming write appends.
- **FR-013**: System MUST execute deterministic entity resolution linking client accounts sharing cryptographic tax IDs, normalized phone numbers, or email hashes.
- **FR-014**: System MUST execute probabilistic record linkage (Fellegi-Sunter / Splink) for records sharing device fingerprints and high name similarity ($\ge 0.88$ Jaro-Winkler).
- **FR-015**: System MUST implement a Hub Suppression algorithm that tags devices or IP addresses linked to $\ge 5$ distinct identities as `is_shared_context=True` and prevents false entity merges.
- **FR-016**: System MUST maintain canonical client entity records (`CanonicalClientEntity`) with persistent lineage links back to source platform accounts (MT5, Deriv Trader, DP2P).
- **FR-017**: System MUST pseudonymize all fields marked under `Marking P` using deterministic HMAC-SHA256 tokenization before persisting to hot state or exposing via APIs.
- **FR-018**: System MUST ensure that identical raw PII values generate identical surrogate tokens across all data products to preserve relational joins.
- **FR-019**: System MUST isolate raw PII inversion keys in a secure token vault with mandatory access auditing.
- **FR-020**: System MUST compute real-time freshness lag ($T_{\text{now}} - T_{\text{event}}$) for each data product and flag SLA violations when lag exceeds configured thresholds.
- **FR-021**: System MUST expose a Data Quality status endpoint (`GET /v1/dq/status`) returning freshness, breach counts, null rates, and entity conflict metrics across all 14 data products.
- **FR-022**: System MUST export micro-batched hot state to partitioned Parquet files accompanied by immutable `_lineage.json` metadata records.
- **FR-023**: System MUST handle duplicate event deliveries idempotently based on unique event identifiers and timestamps.
- **FR-024**: System MUST sanitize and normalize incoming text fields (UTF-8 encoding, stripping null bytes and illegal control characters).

---

### Key Entities

- **`DataProductEvent`**: An individual operational event (trade, deposit, click, telemetry) tagged with product name, schema version, timestamp, tenant ID, and payload.
- **`ContractBreachRecord`**: An invalid event diverted to DLQ, enriched with timestamp, error messages, failing field paths, raw payload bytes, and client IP.
- **`DataProductContract`**: The formal specification for a data product, defining Pydantic model class, required fields, null-rate limits, freshness SLA, and security markings.
- **`HotStateTable`**: A registered columnar table within in-memory DuckDB (`:memory:eios_hot_state`), indexed for time-series and entity lookups.
- **`CanonicalClientEntity`**: The resolved golden customer record representing a single trader, linking MT5 account numbers, Deriv Trader logins, DP2P user IDs, and device hashes.
- **`EntityLinkageCandidate`**: A pair of records evaluated for linkage, containing comparison scores (exact key match, name Jaro-Winkler, device similarity) and hub suppression flags.
- **`PseudonymToken`**: A surrogate identifier replacing raw PII, computed via deterministic HMAC-SHA256 with key versioning.
- **`DataQualityReport`**: A structured snapshot of platform data health, containing per-product freshness lag, breach rates, record volume, and status (`HEALTHY`, `DEGRADED`, `CRITICAL`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Event ingestion latency p95 is $\le 30\text{ seconds}$ from generation time to queryable presence in the hot-state analytical buffer `[TARGET]`.
- **SC-002**: Exactly 100% of contract breaches are caught by the validation gate and routed to the Dead-Letter Queue with zero records silently discarded `[TARGET]`.
- **SC-003**: Hot-state rehydration completes in $< 3.0\text{ seconds}$ on container startup for $\ge 100,000$ baseline Parquet records (ADR-012) `[TARGET]`.
- **SC-004**: Entity resolution achieves $\ge 98.0\%$ precision and $\ge 95.0\%$ recall on cross-platform identity linking against seeded ground-truth evaluation sets `[TARGET]`.
- **SC-005**: False merge rate on shared-device family and shared-IP clusters is $\le 0.1\%$ under the hub suppression algorithm `[TARGET]`.
- **SC-006**: Exactly 100% of PII fields under `Marking P` are pseudonymized prior to insertion into hot state or exposure to downstream reasoning agents `[TARGET]`.
- **SC-007**: When a data product breaches its contract or freshness SLA, its status transitions to `DEGRADED` within $\le 5.0\text{ seconds}$ `[TARGET]`.
- **SC-008**: The automated test suite achieves $\ge 80\%$ line and branch coverage across all Layer 1 modules, executed via `uv run pytest` `[TARGET]`.

---

## Assumptions

- **Upstream Event Formatting**: Upstream generators (from Layer 0 Foundry) produce events conforming to the 14 Layer 1 data product schemas with known seed metadata.
- **Storage Subsystem**: In local dev and test environments, GCS and Pub/Sub are simulated using in-process emulators and local directory paths (`data/raw/` and memory queues), while adhering to GCP production client interfaces.
- **Single Process Hot State**: The DuckDB hot-state engine runs in-process inside the FastAPI container revision, utilizing named in-memory connections (`:memory:eios_hot_state`) or shared local memory mapped files.
- **Token Vault Encryption**: HMAC secret keys for pseudonymization are managed via environment configuration or Secret Manager, rotated with version identifiers.
