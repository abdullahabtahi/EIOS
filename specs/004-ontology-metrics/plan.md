# Implementation Plan: Layer 2 Kinetic Ontology & Semantic Metric Layer (F03)

**Branch**: `004-ontology-metrics` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-ontology-metrics/spec.md`

---

## Summary

Feature F03 establishes the **Layer 2 Kinetic Ontology & Semantic Metric Layer**, delivering the enterprise operating system's four-fold integration of **Data, Logic, Action, and Security** (`docs/foundry.md`) per `initial_plan.md` §3.3 (L2), §4, `docs/data_products_and_omcp.md`, and `docs/engagement_plan.md`.

F03 operationalizes the Palantir Ontology and McKinsey *Rewired* Tier 2 architecture:
- **Governed Semantic Metric Registry (`eios.ontology.metrics`)**: Replaces external heavy semantic daemons with an in-process, vectorized DuckDB metric engine (ADR-003 / Spike S-02). Executes governed KPI queries in $\le 5\text{ms}$ with full versioning, mathematical determinism, and zero hallucination risk (`FR-001`–`FR-005`, `SC-001`).
- **Kinetic Ontology Core & Interfaces (`eios.ontology.core`)**: Implements strongly-typed schemas for 13 canonical Object Types (`ClientAccount`, `Device`, `IPAddress`, `PaymentMethod`, `Partner`, `SubAffiliate`, `Competitor`, `Product`, `Region`, `Case`, `Alert`, `Decision`, `MacroEvent`) and 9 Link Types, with polymorphic interfaces (`TransactingEntity`, `AuditableEntity`) (`FR-006`–`FR-010`).
- **In-Memory Property Graph with Hub Suppression (`eios.ontology.graph`)**: NetworkX in-memory property graph rehydrating from hot state in $< 1.5\text{s}$ (ADR-004 / Spike S-04). Implements degree-based Hub Suppression (degree $\ge 5$, `is_shared_context=True`) on carrier-grade NATs and shared devices, capping false merges at $\le 0.1\%$ per ADR-008 (`FR-011`–`FR-015`, `SC-004`, `SC-005`, `SC-006`).
- **Deterministic Server-Side Functions (`eios.ontology.functions`)**: Pure, stateless Python functions (`partner_value_at_risk`, `ring_membership`, `client_quality_score`, `churn_priority`, `scenario_propagate`) executing business logic in $\le 5\text{ms}$ per object evaluation (`FR-016`–`FR-018`).
- **Metric Auditor Gate (`eios.ontology.auditor`)**: Mandatory egress firewall implementing Constitution Principle I and Red-Line test RL-1. Parses all numeric tokens from agent narratives and blocks 100% of unanchored or hallucinated figures (`FR-019`–`FR-023`, `SC-002`).
- **Governed Action Intent Hub (`eios.ontology.actions`)**: Non-autonomous mutation interface implementing Constitution Principle II. Emits Cloud KMS ECDSA P-256 signed `ActionIntentToken`s with 15-minute validity windows, nonce-bound replay prevention, and four-eyes human approval for High severity actions (`FR-024`–`FR-028`, `SC-003`).
- **OMCP Tool Surface & Security Marking Gateway (`eios.ontology.omcp`)**: Exposes the 13 canonical OMCP tools with server-side enforcement of `PII`, `SENSITIVE_COMPLIANCE`, and `PARTNER_COMMERCIAL` markings, preserving Layer 1 token vault pseudonymization (`FR-029`–`FR-031`, `SC-007`).

---

## Technical Context

**Language/Version**: Python 3.11+ / 3.14 (platform standard).

**Primary Dependencies**: `duckdb>=1.1.0`, `networkx>=3.2.0`, `pydantic>=2.13.5`, `cryptography>=43.0.0`, `fastapi>=0.142.2`, `polars>=0.20.0`, `numpy>=1.26.0`, `uvicorn>=0.54.0`. Tooling: `pytest` with `pytest-cov`, `ruff`, `mypy`. Rationale and alternatives documented in [research.md](./research.md).

**Storage**: In-memory columnar DuckDB (`:memory:eios_hot_state`), in-memory NetworkX property graph, in-memory Action Intent cache / Firestore, append-only Decision Ledger.

**Testing**: `pytest` covering unit, property-graph, contract, auditor-gate, and action-intent tiers under `tests/ontology/`; adversarial hallucination test suites; coverage gate $\ge 80\%$ line and branch `[TARGET]`.

**Target Platform**: Google Cloud Run container (`linux/amd64` / `linux/arm64`) and developer workstations (macOS/Linux).

**Project Type**: Reusable core platform package (`eios.ontology`) and OMCP service gateway (`eios.ontology.omcp`).

**Performance Goals**:
- Metric query latency p95 $\le 10\text{ms}$ against 100,000 records `[TARGET]`.
- Property graph rehydration $< 1.5\text{s}$ on cold boot for 50,000 nodes and 150,000 edges `[TARGET]`.
- Multi-hop graph traversal (up to 2 hops with hub suppression) $\le 25\text{ms}$ p95 `[TARGET]`.
- Server-side deterministic ontology functions $\le 5\text{ms}$ per object evaluation `[TARGET]`.
- Auditor Gate numeric span matching $\le 2\text{ms}$ per response `[TARGET]`.

**Constraints**:
- Exactly 100% of unanchored or hallucinated numeric claims blocked by Auditor Gate (`Principle I`, `Red-Line RL-1`).
- Zero autonomous execute tools exposed in OMCP tool surface (`Principle II`).
- Zero plaintext PII exposed through OMCP tools (`Principle IV`, `Marking P`).
- False-merge rate on carrier-grade NATs and shared devices $\le 0.1\%$ (`Hub Suppression`).

**Scale/Scope**: 13 canonical Object Types, 9 Link Types, 7 Action Types, 10 Governed Metrics, 13 OMCP Tools.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Principle / Constraint | Pre-research | Post-design |
|---|---|---|---|
| **G1** | **I. LLMs never compute business metrics.** Layer 2 provides Governed Metric Registry and Metric Auditor Gate; blocks 100% of unanchored figures (Red-Line RL-1). | PASS | PASS: Vectorized DuckDB calculations; Auditor Gate regex/span matcher blocks unanchored numbers. |
| **G2** | **II. No autonomous write-back.** Layer 2 exposes propose-only tools; all mutations require Cloud KMS ECDSA P-256 signed Action Intent Tokens and four-eyes human approval. | PASS | PASS: Validated in `contracts/action-intent-token.schema.json` and `data-model.md` §3. |
| **G3** | **III. Honest uncertainty & Causal Gate.** Metric calculations return exact definition versions and audit timestamps; unanswerable queries return typed errors rather than hallucinated approximations. | PASS | PASS: `get_metric` and `run_scenario` return explicit bounds, assumptions, and audit metadata. |
| **G4** | **IV. Data as a product, Ontology access.** Agents access data exclusively through OMCP tools; security markings (`PII`, `SENSITIVE_COMPLIANCE`, `PARTNER_COMMERCIAL`) filtered server-side. | PASS | PASS: Defined in `contracts/omcp-tools.json` with role-based field filtering. |
| **G5** | **V. Provenance and labelling.** Every metric carries formula versions, grain, owner role, and source product citation; figures carry `[TARGET]`, `[BRIEF]`, etc. | PASS | PASS: `contracts/metric-registry-catalog.md` and `data-model.md` §2. |
| **G6** | **VI. Eval-first, anti-circularity (NON-NEGOTIABLE).** Red-first tests, $\ge 80\%$ coverage; Auditor Gate tested against adversarial numerical injections; hub suppression tested against hard negatives. | PASS | PASS: Validated in `quickstart.md` Scenarios 2 & 3. |
| **G7** | **VII. Specialised agents & decoupled pipelines.** Deterministic ontology functions and metric queries are cleanly decoupled from cognitive LLM reasoning loops. | PASS | PASS: OMCP tool contracts enforce strict typing and boundary decoupling. |
| **G8** | **VIII. Deterministic fallback & operability.** Sub-1.5s NetworkX property graph rehydration on container cold boot; sub-10ms metric queries; zero background daemons. | PASS | PASS: In-process Python memory architecture documented in `research.md` §1 & §2. |
| **G9** | **Secrets & Identity.** Cloud KMS ECDSA P-256 signing for tokens; approver identity from IdP claims, never request body. | PASS | PASS: `research.md` §4 and token verification state machine. |
| **G10** | **Validation at boundaries.** All OMCP tool parameters validated against JSON Schema contracts; strict typing on all object properties and link traversals. | PASS | PASS: `contracts/omcp-tools.json` and Pydantic v2 core models. |
| **G11** | **Open decisions stay open.** Layer 2 does not fix downstream agent prompts or frontend UI frameworks (ADR-009). | PASS | PASS: Clean, technology-agnostic ontology API surface. |
| **G12** | **Red-Line test readiness.** Directly enforces Red-Line RL-1 (Auditor Gate blocks unanchored figures) and RL-5 (zero PII leakage across OMCP tools). | PASS | PASS: `test_auditor_gate.py` and `test_omcp_tools.py`. |

Result: 100% PASS on all gates. The Complexity Tracking table is not needed.

---

## Project Structure

### Documentation (this feature)

```text
specs/004-ontology-metrics/
├── spec.md                     # Feature specification (31 FRs, 8 SCs)
├── plan.md                     # This file (/speckit-plan output)
├── research.md                 # Phase 0 architectural & library decisions (Spikes S-02, S-04)
├── data-model.md               # Phase 1 data entities, schemas, and state machine
├── quickstart.md               # Phase 1 runnable validation scenarios
├── contracts/
│   ├── omcp-tools.json         # JSON Schema for the 13 OMCP tools
│   ├── action-intent-token.schema.json # JSON Schema for signed Action Intent Tokens
│   └── metric-registry-catalog.md # Governed metric catalog with formulas, grains, and SLAs
├── checklists/
│   └── requirements.md         # Passed quality checklist
└── tasks.md                    # Created by /speckit-tasks (Phase 2)
```

### Source Code (repository root)

```text
FEIOS/
├── src/
│   └── eios/
│       └── ontology/
│           ├── __init__.py             # Public Layer 2 exports
│           ├── core/
│           │   ├── __init__.py
│           │   ├── objects.py          # 13 Object Types (ClientAccount, Partner, etc.)
│           │   ├── links.py            # 9 Link Types & cardinalities
│           │   └── interfaces.py       # Polymorphic interfaces (TransactingEntity, etc.)
│           ├── metrics/
│           │   ├── __init__.py
│           │   ├── registry.py         # Governed Metric Registry catalog & definitions
│           │   └── engine.py           # In-process DuckDB vectorized query compiler
│           ├── graph/
│           │   ├── __init__.py
│           │   ├── property_graph.py   # NetworkX in-memory graph & cold-boot rehydration
│           │   └── hub_suppression.py  # Degree >= 5 filter (is_shared_context=True)
│           ├── functions/
│           │   ├── __init__.py
│           │   └── deterministic.py    # partner_value_at_risk, ring_membership, etc.
│           ├── auditor/
│           │   ├── __init__.py
│           │   ├── gate.py             # Egress firewall verifying numeric provenance
│           │   └── normalizer.py       # Currency, percentage, and suffix parsing
│           ├── actions/
│           │   ├── __init__.py
│           │   ├── intent_hub.py       # propose_action, nonce generator, expiration
│           │   └── signer.py           # Cloud KMS ECDSA P-256 signing & verification
│           └── omcp/
│               ├── __init__.py
│               ├── server.py           # 13 canonical OMCP tool implementations
│               └── markings.py         # Server-side PII and sensitivity filters
└── tests/
    └── ontology/
        ├── __init__.py
        ├── test_objects_and_links.py   # Core ontology schema & interface tests
        ├── test_metric_registry.py     # Governed metric latency & versioning tests
        ├── test_property_graph.py      # Graph rehydration & hub suppression tests
        ├── test_deterministic_fn.py    # Value-at-Risk, churn hazard, and ring scoring tests
        ├── test_auditor_gate.py        # Red-Line RL-1 unanchored number blocking tests
        ├── test_action_intents.py      # Non-autonomous KMS signing & four-eyes tests
        ├── test_omcp_tools.py          # OMCP tool schemas & security marking tests
        └── test_e2e_layer2.py          # End-to-end integration proof
```

**Structure Decision**: Selected standard domain-driven package structure under `FEIOS/src/eios/ontology/` and test suite under `FEIOS/tests/ontology/`, mirroring the successful Layer 1 pattern (`eios.ingestion`).
