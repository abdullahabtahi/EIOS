# Implementation Plan: Executive Cockpit & Operator Workstations (F11 / Slice S6)

**Branch**: `012-cockpit` | **Date**: 2026-10-09 | **Spec**: [specs/012-cockpit/spec.md](spec.md)

**Input**: Feature specification from `specs/012-cockpit/spec.md`, `initial_plan.md` §7, §6.1–6.3, `docs/archive/initial_plan_v2.md` §6, `docs/brief/monitoring.md`, `docs/brief/fraud.md`, `.specify/memory/constitution.md` (Principles I, II, III, IV, V, VI, VII, VIII).

---

## 1. Summary

Deliver **Executive Cockpit & Operator Workstations** (F11 / Slice S6), establishing the institutional Common Operational Picture (COP) for the Enterprise Intelligence Operating System. Adhering strictly to user mandates and institutional design doctrines (Palantir Foundry Solution Designer $\times$ McKinsey QuantumBlack Design System `QBDS`), the interface enforces a high-density, **pure light-mode design system** (`#ffffff` panel cards, `#f4f6f8` ground, `#1c2530` slate-navy rail, high-contrast `#0f172a` text, crisp `#e2e8f0` dividers, sharp 0px border radius, with **zero dark mode**).

The system implements 5 specialized persona workstations anchored within a unified **Tripartite Common Operational Picture layout** (Left Triage & Anomaly Rail, Center Evidence Copilot Dossier, Right Kinetic Analytical Canvas, and Bottom-anchored Governed Action Shelf):
1. **Executive Decision Cockpit**: 4-horizon Morning Briefing feed (Competitive, Partner, Client, Financial), 4-domain causal DAG with DoWhy refuter validation status, interactive What-If Shock Slider executing parametric propagation in $<200$ ms, mathematically guaranteed 100% additive attribution waterfall, and strategic trade-off cards.
2. **AML Investigator Workstation**: Discrepancy-ranked triage queue, 1-screen unified entity dossier (KYC/KYB, fiat/crypto transaction velocity, pseudonymized `tok_id_cluster_<hex16>`), kinetic network graph with dynamic hub suppression for high-degree nodes ($> 100$), regulator-ready SAR draft composer with verified citations, and 2PC `HoldWithdrawal` action modal.
3. **Partner Manager Workstation**: Value $\times$ Risk Churn Radar scatter plot with 14-day intervention countdowns, cohort decay map, partner referral tree with opposite/mirror-trading ring detection, and governed retention playbook recommender.
4. **Compliance & Audit Explorer**: Monotonic ledger timeline (`ledger_seq = 1, 2, 3...`), interactive SHA-256 hash chain verification bar, WORM compliance checkpoint proofs (GCS Object Retention Lock), and Four-Eyes dual-approval audit trail.
5. **Data Platform & Operations Board**: Real-time Data Quality (DQ) board, contract breach alerts, ingestion freshness SLA monitors with automatic `DEGRADED` badging, Identity Cluster conflict inspector, and semantic metric catalog lineage topology.

Cross-cutting invariants enforce:
- **Instant Deterministic Metric Provenance Popovers** ($< 50$ ms) on every scalar metric.
- **Metric Auditor Gate** intercepting and blocking ungrounded numeric claims in agent narratives.
- **No Autonomous Write-Back**: Mutations stage as Cloud KMS signed `ActionIntentToken` review cards requiring Four-Eyes dual human approval for High-severity actions.
- **Deterministic Replay Fallback**: Outages degrade gracefully to precomputed snapshots stamped with prominent amber `[REPLAY]` badges.
- **Technology-Agnostic Core**: Preserves open architectural decisions `ADR-009` (frontend stack) and `ADR-014` (API transport: REST+SSE vs GraphQL+SSE).

---

## 2. Technical Context

**Language/Version**: Python 3.11+ (running on Python 3.14.4 in active project virtualenv)  
**Primary Dependencies**:
- `pydantic>=2.13.5` (Strict domain entity schemas, JSON Schema export, and input validation)
- `duckdb>=1.1.0` (Analytical query engine powering HotState and sub-5ms metric aggregations)
- `fastapi` / `starlette` / `mcp` (Cockpit API services, SSE event streaming, and canonical OMCP tool exposures)
- `networkx` (Kinetic graph topology, Louvain community detection, and degree-based hub suppression)
- `scipy` / `numpy` (Parametric causal shock propagation and attribution waterfall normalization)

**Storage**:
- DuckDB Hot State & Semantic Registry:
  - `cockpit_workstation_views` (session cache, filter presets, and active triage queues)
  - `morning_briefing_snapshots` (versioned 4-horizon briefings and historical morning summaries)
  - `atomic_sequence_ledger` & `worm_anchor_checkpoints` (auditable decision ledger and WORM proofs)
  - `governed_action_intents` (active two-phase commit tokens, nonces, and approval states)
  - `data_product_sla_registry` (contract schemas, null-check scores, and freshness SLA records)

**Testing**:
- `pytest`, `pytest-cov`, `pytest-xdist` with $\ge 80\%$ line and branch coverage gate `[TARGET]`
- Dedicated test suites covering light-mode design tokens, provenance popover latency, what-if shock propagation, AML dossier assembly, dynamic hub suppression, 2PC action shelf transitions, and replay fallback under simulated outages.

**Target Platform**: Linux Server / macOS / Google Cloud Run containerized workers  
**Performance Goals**:
- Deterministic Metric Provenance Popover Resolution: $< 50\,\text{ms}$ p95 `[TARGET]`
- Interactive What-If Shock Parametric Propagation: $< 200\,\text{ms}$ `[TARGET]`
- 1-Screen AML Entity Dossier Assembly: $< 150\,\text{ms}$ `[TARGET]`
- Kinetic Graph Interaction: $> 30\,\text{FPS}$ with hub suppression for up to 1,000 entities `[TARGET]`
- Cryptographic Hash Chain Verification (10,000 records): $< 1.0\,\text{s}$ `[TARGET]`
- Forecast Attribution Waterfall Mathematical Precision: Exactly $100.00\% \pm 0.01\%$ `[TARGET]`

**Constraints**:
- **Constitution Principle I**: Zero LLM math (every number displayed must resolve to deterministic tool or ontology query) `[TARGET]`
- **Constitution Principle II**: Strict non-autonomous write-back; Two-Phase Commit with Four-Eyes dual approval for High-severity actions `[CONSTITUTION Principle II]`
- **Constitution Principle III**: Honest uncertainty; causal edges passing refuters render as solid vectors; unverified links render as dashed correlations `[CONSTITUTION Principle III]`
- **Constitution Principle IV**: Data products consumed exclusively via contracts/OMCP; direct raw DB mutations prohibited
- **Constitution Principle VII**: Decoupled pipelines; SCM structure and refutations fitted offline in batch; online slider runs fast parametric propagation
- **Constitution Principle VIII**: Deterministic replay fallback with amber `[REPLAY]` badging during simulated LLM/gateway outages
- **Institutional Aesthetics**: Strict high-contrast light mode (`#ffffff` panel cards, `#f4f6f8` ground, `#1c2530` slate-navy rail, 0px border radius, zero dark mode)
- **Open Architectural Decisions**: `ADR-009` and `ADR-014` remain strictly open and unbreached

**Scale/Scope**:
- 5 persona workstations, 10 canonical domain entities, 10 JSON Schema contracts, 6 end-to-end validation scenarios, and complete OMCP tool integration.

---

## 3. Constitution Check

*GATE: Evaluated against `.specify/memory/constitution.md`.*

- **Principle I (LLMs Never Compute Business Metrics)**: **PASS**. Every metric rendered in the cockpit is verified against the Semantic Metric Registry. Hovering/clicking triggers an instant Provenance Popover. The Metric Auditor Gate masks unverified figures in agent narratives.
- **Principle II (No Autonomous Write-Back - NON-NEGOTIABLE)**: **PASS**. All mutation actions stage in the Governed Action Shelf as Cloud KMS signed `ActionIntentToken` review cards. High-severity actions require two distinct human approvers before committing to the simulated write-back sink.
- **Principle III (Honest Uncertainty & Causal-Evidence Gate)**: **PASS**. The Executive causal DAG renders solid causal arrows only when passing refuter gates (placebo effect $\approx 0$, confidence $\ge 0.80$). Unrefuted links are explicitly labelled as correlations.
- **Principle IV (Data as a Product, Ontology-Only Access)**: **PASS**. Workstations consume data products strictly through contracts and OMCP tools. Contract breaches and SLA delays immediately flag products as `DEGRADED`.
- **Principle V (Provenance & Labelling)**: **PASS**. 100% of rendered quantitative figures carry `ProvenanceMetadata` (`metric_id`, version, timestamp, steward). All numbers in docs and tests carry explicit provenance labels (`[TARGET]`, `[BRIEF]`, `[ILLUSTRATIVE]`).
- **Principle VI (Eval-First, Baselines & Coverage - NON-NEGOTIABLE)**: **PASS**. Comprehensive automated test suites are defined before implementation with an $\ge 80\%$ test coverage requirement and zero regressions against existing baselines.
- **Principle VII (Specialized Agents & Decoupled Pipelines)**: **PASS**. The cockpit aggregates outputs from specialized domain agents behind the Supervisory Router. Interactive what-if sliders use precomputed cached SCM coefficients for sub-200ms parametric propagation.
- **Principle VIII (Deterministic Fallback & Operability)**: **PASS**. Service outages trigger the Deterministic Fallback Engine, rendering verified cached snapshots with prominent amber `[REPLAY]` badges rather than invented text.

---

## 4. Project Structure & Deliverables

### Documentation (`specs/012-cockpit/`)
```text
specs/012-cockpit/
├── plan.md                                           # This architectural implementation plan
├── research.md                                       # Phase 0 architectural trade-offs & design decisions
├── data-model.md                                     # Phase 1 Pydantic v2 domain schemas & state transitions
├── quickstart.md                                     # Phase 1 runnable validation scenarios
├── checklists/
│   └── requirements.md                               # Quality requirements checklist
└── contracts/                                        # Phase 1 JSON Schema interface specifications
    ├── workstation-view-session.schema.json          # Active operator session & tab state schema
    ├── provenance-metadata.schema.json               # Deterministic metric provenance record schema
    ├── morning-briefing-dossier.schema.json          # 4-horizon morning briefing dossier schema
    ├── causal-dag-graph.schema.json                  # Causal DAG network with refuter status schema
    ├── entity-investigation-dossier.schema.json      # 1-screen unified AML entity dossier schema
    ├── kinetic-network-graph.schema.json             # Kinetic graph with hub suppression schema
    ├── sar-draft-document.schema.json                # Regulator-ready SAR draft document schema
    ├── churn-radar-scatter.schema.json               # Partner churn radar scatter dataset schema
    ├── governed-action-card.schema.json              # Staged 2PC ActionIntentToken card schema
    └── data-product-sla-status.schema.json           # Data product SLA & health status schema
```

### Source Code (`FEIOS/src/eios/cockpit/`)
```text
FEIOS/src/eios/cockpit/
├── __init__.py                                       # Package exports for Cockpit module
├── session.py                                        # WorkstationViewSession manager with RBAC
├── tokens.py                                         # Institutional Light-Mode Design Token Registry (Palantir × QBDS)
├── provenance.py                                     # Deterministic Metric Provenance Resolver (< 50ms cache)
├── executive.py                                      # Executive Decision Cockpit service (Briefing, DAG, What-If, Attribution)
├── aml.py                                            # AML Investigator Workstation service (Dossier, SAR, Hub-Suppressed Graph)
├── partner.py                                        # Partner Manager Workstation service (Churn Radar, Hierarchy, Playbooks)
├── compliance.py                                     # Compliance & Audit Explorer service (Ledger timeline, Hash verifier)
├── operations.py                                     # Data Platform & Operations Board service (DQ board, SLAs, Lineage)
├── governance_shelf.py                               # Governed Action Shelf presenter (2PC state machine & Four-Eyes review)
└── fallback.py                                       # Deterministic Replay & Cached Fallback engine ([REPLAY] badges)
```

### Test Suites (`FEIOS/tests/cockpit/`)
```text
FEIOS/tests/cockpit/
├── __init__.py                                       # Cockpit test package
├── test_design_tokens.py                             # Institutional light-mode token compliance & contrast ratio tests
├── test_metric_provenance.py                         # Provenance popover sub-50ms latency & Auditor Gate tests
├── test_executive_what_if.py                         # What-if shock parametric propagation & 100% attribution tests
├── test_aml_workstation.py                           # 1-screen dossier assembly & kinetic graph hub suppression tests
├── test_partner_workstation.py                       # Churn radar scatter & partner hierarchy ring tests
├── test_compliance_explorer.py                       # Ledger timeline & interactive hash chain verification tests
├── test_operations_board.py                          # DQ board, SLA monitoring, and lineage topology tests
├── test_governed_action_shelf.py                     # Two-phase commit action staging & Four-Eyes modal tests
└── test_cockpit_fallback.py                          # Outage simulation, cached snapshots, and [REPLAY] badging tests
```

---

## 5. Structure Decision

We encapsulate all cockpit aggregation services, layout token definitions, provenance resolvers, and workstation view builders in a dedicated domain module `FEIOS/src/eios/cockpit/`, maintaining clean separation of concerns. This module sits directly on top of `ontology/`, `synthesis/`, `aml/`, `fraud/`, `churn/`, and `actions/`, aggregating hot-state analytical datasets into typed presentation models. All client contracts are exposed via strict JSON Schemas, keeping the frontend stack choice (`ADR-009`) and API protocol transport (`ADR-014`) completely open.

---

## 6. Complexity Tracking

| Requirement / Invariant | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Dynamic Hub Suppression ($k > 100$)** | High-degree payment agents and shared CGNAT IPs create hairballs with $>500$ links that freeze rendering canvases. | Naive unconstrained force-directed layouts cause visual clutter, browser freezes, and unreadable investigative graphs. |
| **Sub-200ms Parametric What-If Propagation** | Executives need fluid slider interaction without waiting for batch causal discovery. | Live DoWhy structural refutation takes 10–30s per turn, making interactive sliders completely unusable. |
| **Client-Side Deterministic Provenance Cache** | Operators expect instant ($<50$ms) inspection when hovering over any metric scalar. | Asynchronous round-trip API queries add 200–500ms network latency, making rapid table inspection feel sluggish. |
| **Deterministic Replay Fallback with `[REPLAY]` Badging** | Enterprise operators must maintain situational awareness during external LLM outages. | Error pages halt investigations, and ungrounded fallback LLM prompts violate Constitution Principle I. |
