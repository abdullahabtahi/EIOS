# Tasks: Layer 1 Ingestion Spine & Contract Gateway (F02)

**Input**: Design documents from `/specs/003-contracts-ingestion/`  
**Path convention**: Every code, config, docs, infra, and test path in this file is relative to `FEIOS/` (the platform repository root). Planning documents (`specs/`, `initial_plan.md`, `docs/`) stay at the workspace root.  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present and verified)  
**Tests**: MANDATORY. Constitution Principle VI requires test-first (RED $\rightarrow$ GREEN $\rightarrow$ refactor). Every implementation task is preceded by a test task that must fail first. Coverage gate is $\ge 80\%$ line and branch coverage `[TARGET]`.  
**Organisation**: Grouped by user story (US1..US6) following priority order, enabling independent implementation and testing of each story.

## Format: `- [ ] T### [P?] [US#?] Description with file path`

- `[P]`: Can run in parallel (different files, no unmet dependencies).
- `[US#]`: User story label. Present only in story phases (Phases 3 to 8). Absent in Setup, Foundational, and Polish.
- "RED" in a test task means: write the test, run it, and confirm it fails for the right reason before starting the matching implementation task.

---

## Phase 1: Setup (Layer 1 Ingestion Skeleton & Dependencies)

**Purpose**: Initialize the Layer 1 Ingestion and Contract library directory structure, dependencies, and configuration templates.

- [X] T001 Create directory skeleton for Layer 1: `src/eios/ingestion/`, `src/eios/ingestion/entity_resolution/`, `src/eios/contracts/`, and `tests/contracts/`.
- [X] T002 Add `duckdb>=1.1.0` and `cryptography>=43.0.0` to `pyproject.toml` dependencies and run `uv sync`.
- [X] T003 [P] Configure module exports in `src/eios/ingestion/__init__.py` and `src/eios/contracts/__init__.py`.
- [X] T004 [P] Copy JSON Schemas and OpenAPI spec from `specs/003-contracts-ingestion/contracts/` into `schemas/` (`dlq-envelope.schema.json`, `ingestion-api.json`).

---

## Phase 2: Foundational (Core Config, Base Contract Models, and Shared Fixtures)

**Purpose**: Shared core infrastructure required by all ingestion workers, contract validators, and user stories.

### Tests first (RED)

- [X] T005 [P] Write `tests/contracts/test_base_contracts.py`: test serialization, timestamp parsing, tenant validation (`DERIV_MFSA`, `DERIV_LFSA`, `DERIV_VFSC`), and base contract models. RED.
- [X] T006 [P] Write `tests/contracts/conftest.py`: pytest fixtures for mock Pub/Sub topics, test Parquet partitions, in-memory DuckDB connections, and mock HMAC token salt.

### Implementation (GREEN)

- [X] T007 [P] Implement `src/eios/ingestion/config.py`: configuration management (Pub/Sub topic IDs, DLQ topic, warm-start data path, flow control parameters, port, secret keys).
- [X] T008 [P] Implement `src/eios/contracts/base.py`: `DataProductEvent` base envelope, `TenantEnum`, `DataProductEnum`, and serialization helpers. Makes T005 pass.
- [X] T009 [P] Implement `src/eios/contracts/models.py`: Pydantic v2 schemas for all 14 L1 data products (`Client360Event`, `TransactionAMLEvent`, `TradingActivityEvent`, etc.) per `l1-data-product-contracts.md`.
- [X] T010 Run `uv run pytest tests/contracts/test_base_contracts.py -q` to verify foundational contracts pass.

**Checkpoint**: Foundational layer green. User Story implementation can begin.

---

## Phase 3: User Story 1 - Real-Time Multi-Modal Event Ingestion (Priority: P1) 🎯 MVP

**Goal**: Deliver a dual-path ingestion gateway supporting asynchronous Pub/Sub pull with flow control and high-performance synchronous FastAPI push webhooks (`POST /v1/events/ingest`) delivering sub-50ms acknowledgements (`FR-001`, `FR-002`, `SC-001`).

**Independent Test**: Send 1,000 trade events through the push webhook and 1,000 transaction events through the asynchronous subscriber. Assert that all 2,000 events are acknowledged, micro-batched, and accessible in the staging pipeline within target latency.

### Tests first (RED)

- [X] T011 [P] [US1] Write `tests/contracts/test_router.py`: test synchronous `POST /v1/events/ingest` endpoint accepts single events and arrays, returns HTTP 202 in $\le 50\text{ms}$, and rejects non-JSON payloads with HTTP 400. RED.
- [X] T012 [P] [US1] Write `tests/contracts/test_subscriber.py`: test asynchronous Pub/Sub subscriber consumes messages with flow control, calls `ack()` on processed events, and calls `nack()` on transient errors. RED.

### Implementation (GREEN)

- [X] T013 [US1] Implement `src/eios/ingestion/queue.py`: thread-safe in-memory bounded staging micro-batch queue with configurable flush interval (500ms or 250 records).
- [X] T014 [US1] Implement asynchronous Pub/Sub subscriber worker in `src/eios/ingestion/subscriber.py` using `google.cloud.pubsub_v1.SubscriberClient` with `FlowControl(max_messages=1000, max_bytes=10MB)`. Makes T012 pass.
- [X] T015 [US1] Implement FastAPI ingestion application & router in `src/eios/ingestion/router.py` exposing `POST /v1/events/ingest` and mounting liveness probe `/healthz`. Makes T011 pass.
- [X] T016 [US1] Run `uv run pytest tests/contracts/test_router.py tests/contracts/test_subscriber.py -q` to verify User Story 1 MVP passes.

**Checkpoint**: User Story 1 MVP is fully testable and operational.

---

## Phase 4: User Story 2 - Contract Validation Gate & Zero-Drop DLQ Circuit Breaker (Priority: P1)

**Goal**: Enforce strict Pydantic contract validation across all 14 data products, diverting 100% of breaching payloads to Dead-Letter Queue `eios.l1.dlq.v1` with structured Cloud Logging and toggling product health to `DEGRADED`, with zero silent drops (`FR-003`–`FR-007`, `SC-002`).

**Independent Test**: Feed 500 valid records and 50 malformed records (null required fields, negative deposit amounts, schema type errors). Assert that 500 records pass into hot state, exactly 50 records land in the DLQ with structured error reasons, and the product status is flagged as `DEGRADED`.

### Tests first (RED)

- [X] T017 [P] [US2] Write `tests/contracts/test_contract_gate.py`: test validation gate verifies all 14 data product contracts, catches type errors, null violations, missing fields, and range breaches. RED.
- [X] T018 [P] [US2] Write `tests/contracts/test_dlq.py`: test invalid events are never dropped, generate `ContractBreachRecord` matching `dlq-envelope.schema.json`, publish to `eios.l1.dlq.v1`, and emit structured Cloud Logging JSON. RED.

### Implementation (GREEN)

- [X] T019 [US2] Implement `src/eios/ingestion/validator.py`: high-throughput Pydantic v2 `TypeAdapter` validation engine with field-path error extraction and schema catalog. Makes T017 pass.
- [X] T020 [US2] Implement `src/eios/ingestion/dlq.py`: Dead-Letter Queue dispatcher, JSON envelope builder matching `schemas/dlq-envelope.schema.json`, and structured Cloud Logging emitter. Makes T018 pass.
- [X] T021 [US2] Implement circuit breaker in `src/eios/ingestion/circuit_breaker.py`: calculates rolling 1-hour breach rates per product and toggles status to `DEGRADED` when breach rate $> 0.05\%$.
- [X] T022 [US2] Run `uv run pytest tests/contracts/test_contract_gate.py tests/contracts/test_dlq.py -q`.

**Checkpoint**: User Stories 1 and 2 are fully integrated; contract enforcement is green.

---

## Phase 5: User Story 3 - In-Memory Hot-State Engine with Parquet Warm-Start Rehydration (Priority: P1)

**Goal**: Deliver in-process DuckDB columnar hot state (`:memory:eios_hot_state`) rehydrated from Parquet lakehouse snapshots in $< 3.0\text{s}$ for $\ge 100,000$ records on container cold boot per ADR-012, backed by container readiness probes (`/readyz`) and liveness probes (`/healthz`) (`FR-008`–`FR-012`, `SC-003`).

**Independent Test**: Measure the exact elapsed wall-clock time required to initialize `:memory:eios_hot_state` from 100,000 records of synthetic Parquet files on cold start. Execute concurrent analytical SQL queries across multiple reader threads and assert zero corruption or race conditions.

### Tests first (RED)

- [X] T023 [P] [US3] Write `tests/contracts/test_warm_start.py`: benchmark cold-boot rehydration of 100,000 synthetic Parquet records into `:memory:eios_hot_state` in $< 3.0\text{s}$ (ADR-012), verifying `/readyz` probe state (503 while loading, 200 when ready). RED.
- [X] T024 [P] [US3] Write `tests/contracts/test_hot_state.py`: test concurrent multi-threaded DuckDB reading and writing, sliding window eviction (24h/30d), and sub-15ms p95 analytical query latency. RED.

### Implementation (GREEN)

- [X] T025 [US3] Implement `src/eios/ingestion/hot_state.py`: DuckDB engine manager maintaining `:memory:eios_hot_state`, registering all 14 product tables, and providing connection pooling / cursors. Makes T024 pass.
- [X] T026 [US3] Implement Parquet warm-start loader in `src/eios/ingestion/warm_start.py`: scans partitioned lakehouse snapshots (`data/raw/<product>/*.parquet`), executes vectorized `read_parquet()` insertion, and tracks load duration. Makes T023 pass.
- [X] T027 [US3] Wire FastAPI `lifespan` in `src/eios/ingestion/router.py`: trigger warm-start on startup, start background subscriber, mount `/readyz` readiness probe, and ensure clean shutdown.
- [X] T028 [US3] Run `uv run pytest tests/contracts/test_warm_start.py tests/contracts/test_hot_state.py -q`.

**Checkpoint**: In-memory hot state and cold-boot warm-start rehydration operational.

---

## Phase 6: User Story 4 - Single Client View (SCV) Entity Resolution with Hub Suppression (Priority: P1)

**Goal**: Deliver a two-stage hybrid entity resolution engine combining deterministic key matching (tax ID, phone, email hashes) with probabilistic Fellegi-Sunter record linkage, enforcing a strict Hub Suppression filter (degree $\ge 5$) on shared family devices and office/CGNAT IPs to cap false merges at $\le 0.1\%$ per ADR-008 (`FR-013`–`FR-016`, `SC-004`, `SC-005`).

**Independent Test**: Process a test batch containing 100 distinct traders with multiple fragmented platform IDs, 10 deliberate multi-accounting syndicates, and a 10-person family sharing a single tablet. Assert that fragmented IDs resolve to single canonical IDs, while family members sharing the tablet remain separate entities with `is_shared_context=True`.

### Tests first (RED)

- [X] T029 [P] [US4] Write `tests/contracts/test_entity_resolution.py`: test deterministic exact key linking (tax ID, phone hash, email hash) and probabilistic record linkage (Jaro-Winkler name $\ge 0.88$, device fingerprint). Verify $\ge 98\%$ precision and $\ge 95\%$ recall. RED.
- [X] T030 [P] [US4] Write `tests/contracts/test_hub_suppression.py`: test hub suppression filter: device or IP connected to $\ge 5$ distinct tax IDs tags `is_shared_context=True` and prevents false merging of family/office accounts (false merge rate $\le 0.1\%$). RED.

### Implementation (GREEN)

- [X] T031 [US4] Implement deterministic exact key resolver in `src/eios/ingestion/entity_resolution/deterministic.py`: builds connected components over high-entropy cryptographic hashes.
- [X] T032 [US4] Implement probabilistic Fellegi-Sunter record linkage in `src/eios/ingestion/entity_resolution/probabilistic.py`: computes match weights, Jaro-Winkler string distances, and classification thresholds. Makes T029 pass.
- [X] T033 [US4] Implement Hub Suppression filter in `src/eios/ingestion/entity_resolution/hub_suppression.py`: evaluates attribute degree in DuckDB and blocks merges on shared devices/IPs. Makes T030 pass.
- [X] T034 [US4] Implement unified SCV coordinator in `src/eios/ingestion/entity_resolution/coordinator.py`: maintains `CanonicalClientEntity` hot-state tables with persistent lineage links back to MT5, Deriv Trader, and DP2P accounts.
- [X] T035 [US4] Run `uv run pytest tests/contracts/test_entity_resolution.py tests/contracts/test_hub_suppression.py -q`.

**Checkpoint**: Single Client View and Hub Suppression operational with verified zero false-merges on shared devices.

---

## Phase 7: User Story 5 - Deterministic PII Pseudonymization Token Vault (Priority: P1)

**Goal**: Deliver deterministic HMAC-SHA256 surrogate tokenization (`tok_client_<hex16>`) for all `Marking P` fields before hot-state persistence or downstream reasoning exposure, guaranteeing zero raw PII leaks into analytical memory or LLM contexts (`FR-017`–`FR-019`, `SC-006`).

**Independent Test**: Feed raw client records containing realistic names, emails, and tax IDs through the pseudonymization service. Inspect the resulting DuckDB tables and verify zero plaintext PII exists. Verify that tokenization of identical identifiers produces identical tokens and that reversing requires high-privilege credentials.

### Tests first (RED)

- [X] T036 [P] [US5] Write `tests/contracts/test_pii_vault.py`: test deterministic HMAC-SHA256 pseudonymization: identical inputs produce identical surrogate tokens (`tok_client_<hex16>`), different inputs produce distinct tokens, and reversing requires secure vault key. RED.
- [X] T037 [P] [US5] Write `tests/contracts/test_pii_leakage.py`: scan DuckDB hot-state tables and API responses to assert zero plaintext emails, phone numbers, or unhashed tax IDs exist (RL-5). RED.

### Implementation (GREEN)

- [X] T038 [US5] Implement `src/eios/ingestion/vault.py`: `TokenVault` managing HMAC-SHA256 blind indexing, AES-256-GCM encrypted persistence, key versioning, and surrogate token generation for `Marking P`. Makes T036 and T037 pass.
- [X] T039 [US5] Integrate Token Vault into `src/eios/ingestion/validator.py` and `src/eios/ingestion/router.py`: automatically pseudonymize `Marking P` fields before hot-state insertion.
- [X] T040 [US5] Run `uv run pytest tests/contracts/test_pii_vault.py tests/contracts/test_pii_leakage.py -q`.

**Checkpoint**: PII Token Vault verified; zero raw PII in hot state or API outputs.

---

## Phase 8: User Story 6 - Real-Time Data Quality (DQ) & Freshness SLA Monitoring Board (Priority: P2)

**Goal**: Deliver real-time Data Quality & Freshness SLA monitoring tracking event lag (p95 $\le 30\text{s}$ SLO), contract breach counters, and null rates across all 14 data products (`GET /v1/dq/status`) and attach immutable `_lineage.json` manifests to Parquet lakehouse batches (`FR-020`–`FR-024`, `SC-007`).

**Independent Test**: Query `/v1/dq/status`. Verify it returns structured health status (`HEALTHY`, `DEGRADED`, `CRITICAL`), p95 freshness lag, total breaches in the last 1 hour, and null-rate counters across all 14 data products.

### Tests first (RED)

- [X] T041 [P] [US6] Write `tests/contracts/test_dq_monitor.py`: test freshness lag computation ($T_{\text{now}} - \max(T_{\text{event}})$), null rate tracking, volume anomaly z-scores, and `/v1/dq/status` endpoint output in $\le 25\text{ms}$. RED.
- [X] T042 [P] [US6] Write `tests/contracts/test_lineage_export.py`: test micro-batched Parquet lakehouse export attaches valid, immutable `_lineage.json` manifests. RED.

### Implementation (GREEN)

- [X] T043 [US6] Implement `src/eios/ingestion/dq.py`: real-time Data Quality & SLA Registry tracking per-product lag, breach counters, null percentages, and `DEGRADED` health state transitions. Makes T041 pass.
- [X] T044 [US6] Mount `/v1/dq/status` in `src/eios/ingestion/router.py`: expose structured operational status JSON for Common Operational Picture and alerting.
- [X] T045 [US6] Implement partitioned Parquet lakehouse exporter in `src/eios/ingestion/exporter.py` with `_lineage.json` manifest generation. Makes T042 pass.
- [X] T046 [US6] Run `uv run pytest tests/contracts/test_dq_monitor.py tests/contracts/test_lineage_export.py -q`.

**Checkpoint**: All 6 User Stories are fully operational and testable.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: System integration, benchmark verification, quickstart validation, and coverage gate enforcement.

- [X] T047 [P] Write end-to-end integration test `tests/contracts/test_e2e_pipeline.py`: replay Layer 0 synthetic event streams through Pub/Sub and webhook, assert contract enforcement, warm-start, entity resolution, PII pseudonymization, and DQ metrics.
- [X] T048 [P] Implement CLI benchmark script in `src/eios/ingestion/cli.py` (`benchmark-warm-start`, `inspect-dlq`, `verify-contracts`, `run-gateway`).
- [X] T049 Execute full Layer 1 test suite with coverage enforcement: `uv run pytest tests/contracts/ --cov=src/eios/ingestion --cov=src/eios/contracts --cov-fail-under=80`.
- [X] T050 Run `specs/003-contracts-ingestion/quickstart.md` validation scenarios and confirm all 6 scenarios succeed.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Stories (Phase 3+)**:
  - **US1 (Ingestion)**: Depends on Phase 2. Delivers the MVP.
  - **US2 (Contracts & DLQ)**: Depends on Phase 2 & US1.
  - **US3 (Hot State & Warm Start)**: Depends on Phase 2 & US2.
  - **US4 (Entity Resolution)**: Depends on US3 (requires DuckDB hot state).
  - **US5 (PII Vault)**: Depends on US2 & US3.
  - **US6 (Data Quality Board)**: Depends on US2 & US3.
- **Polish (Phase 9)**: Depends on all user stories (US1–US6) being complete.

### Parallel Opportunities

- All tests marked `[P]` within a phase can be authored concurrently.
- In Phase 2: Base contract models (`T008`), config (`T007`), and data product models (`T009`) can be authored in parallel.
- In Phase 6: Deterministic resolver (`T031`), probabilistic matcher (`T032`), and Hub Suppression (`T033`) can be implemented in parallel before the coordinator (`T034`).
- In Phase 7: Token Vault (`T038`) can be implemented in parallel with test suite expansion.
