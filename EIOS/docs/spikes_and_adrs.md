# Spikes & Architecture Decision Records

Companion to `initial_plan.md` (planning workspace; not part of this repository, as are the other planning docs cited below). Any claim tagged `[SPIKE]` in the plan (each names its spike, S-01 to S-07) is **unverified** until its spike closes with an ADR. Spikes are time-boxed (`[ASSUMPTION]` ≤ 1 day each unless stated) and happen in S0 before dependent work.

---

## 1. Spikes

| ID | Question | Why unverified | Method | Decision it unlocks | Fallback |
|---|---|---|---|---|---|
| [**S-01**](adr/S-01-llm-availability-and-pricing.md) | Which LLM(s), model IDs, pricing, context caching and rate limits are actually available and affordable? | v2 pinned "Gemini 3.8 Flash via google-genai" without verification | Query provider docs/console; run a 30-prompt latency/cost benchmark through the gateway with tool calling and structured output `[ASSUMPTION]` | ADR-002 (LLM gateway & default models) | Provider-agnostic gateway; default to best verified model per role (router vs synthesis) |
| [**S-02**](adr/S-02-metric-engine-cube-vs-registry.md) | Cube Core vs lightweight metric registry over DuckDB | Cube needs a Node service + CubeStore/Redis; poor fit for scale-to-zero; adds ops cost | Stand up both on 5 KPIs `[ASSUMPTION]`; measure cold start, memory, query latency, ops surface | ADR-003 (metric engine) | Registry contract is the invariant; engine swappable |
| [**S-03**](adr/S-03-design-system-package.md) | Does the referenced external design-system npm package exist | v2 named it without a verified source | Registry search | Input to ADR-009 | Build a small token-based design system |
| [**S-04**](adr/S-04-dowhy-refutation-runtime.md) | DoWhy refutation runtime and stability on our DAG size | Refutation is not sub-second; v2 implied live use | Time nightly fit + refute on synthetic history for N edges; measure variance across seeds | ADR-005 (causal engine & caching) | Cache nightly; live path uses parametric propagation only |
| [**S-05**](adr/S-05-graph-scale-ceiling.md) | Graph scale ceiling for NetworkX + Louvain; hub-suppression effectiveness | In-memory graph vs serverless; shared-IP false merges | Generate graphs 10k → 1M edges `[ASSUMPTION]`; time build/community; compare naive vs hub-suppressed rings | ADR-004 (graph engine), ADR-012 | Snapshot warm start; Spanner Graph / Neo4j as documented alternative |
| [**S-06**](adr/S-06-kms-signing-and-ledger.md) | KMS signing + ledger tamper-evidence + real cost | v2 used symmetric HMAC; BigQuery is not immutable; cost model contradictory | Implement sign/verify with rotation; write-only IAM; hash chain + retention-locked anchor; tamper drill; record real costs over soak | ADR-006, ADR-007, cost-model reconciliation | Firestore-backed append log + anchor if BigQuery constraints bite |
| [**S-07**](adr/S-07-entity-resolution-approach.md) | Entity-resolution approach adequacy (deterministic + probabilistic) | Brief requires ER + DQ flags; no design detail in v2 | Seed duplicates with noise; compare rules vs Fellegi-Sunter (e.g. Splink) | ADR-008 | Deterministic keys + review queue |

Each spike outputs: question, method, data, result, decision, date — stored beside its ADR in `docs/adr/`.

---

## 2. ADR index

Status: **Accepted** = decided; **Proposed** = drafted, awaiting spike/evidence; **Open** = not decided.

| ADR | Decision | Status | Default / current lean | Depends on |
|---|---|---|---|---|
| [ADR-001](adr/001-ontology-as-data-logic-action-security.md) | Ontology as data + logic + action + security (not just a semantic layer) | Accepted | Four-fold per `docs/foundry.md` | — |
| ADR-002 | LLM gateway abstraction & model selection | Open | Provider-agnostic gateway; config-driven models | S-01 |
| ADR-003 | Metric engine (Cube Core vs lightweight metric registry) | Open | In-Process DuckDB Semantic Registry | S-02 |
| ADR-004 | Graph engine (NetworkX vs Neo4j vs Memgraph) | Proposed | NetworkX in-memory | S-05 |
| ADR-005 | Causal engine & offline/online split | Proposed | DoWhy nightly + cached; live parametric propagation | S-04 |
| [ADR-006](adr/006-action-intent-signing.md) | Action Intent signing (Cloud KMS ECDSA P-256, nonce, expiry, rotation) | Accepted | Replaces HMAC | S-06 (verification only) |
| [ADR-007](adr/007-ledger-tamper-evidence.md) | Ledger tamper-evidence (write-only IAM, hash chain, retention-locked anchors) | Accepted | BigQuery + GCS anchors | S-06 |
| ADR-008 | Entity-resolution approach | Open | Deterministic + probabilistic | S-07 |
| ADR-009 | **Frontend stack & design system** | **Open** | No default; decide after §7 persona requirements are stable. `FEIOS/`, `DESIGN.MD`, `DESIGN_PLAN.md` are a website prototype and are not inputs | S-03 |
| [ADR-010](adr/010-approval-service-runtime.md) | Approval service on Cloud Run + Firestore; Cloud Workflows only for scheduled jobs | Accepted | — | — |
| [ADR-011](adr/011-simulated-write-back-sink.md) | Simulated write-back sink as executor (chaos-failable mock core-systems API) | Accepted | — | — |
| [ADR-012](adr/012-warm-start-and-state-strategy.md) | Warm-start & state strategy for in-memory components (Parquet snapshot; min-instances=1 in prod-like) | Accepted | — | S-05 |
| [ADR-013](adr/013-streaming-batch-separation.md) | Streaming vs batch separation and shared hot state | Accepted | Invariant 3 | — |
| ADR-014 | API surface: GraphQL + SSE vs REST + SSE | Open | Decide with ADR-009 | — |
| [ADR-015](adr/015-synthetic-data-split-policy.md) | Synthetic-data split policy (dev/validation/sealed) & anti-circularity controls | Accepted | See `docs/synthetic_data_strategy.md` | — |
| [ADR-018](adr/018-bounded-contexts-and-governed-tool-surface.md) | Bounded contexts and a single governed tool surface | Proposed | Per-context schemas; OMCP is the only agent-facing surface | — |

### ADR template
```
# ADR-NNN: Title
Status: Proposed | Accepted | Superseded by ADR-XXX
Date:
Context: forces, constraints, brief/spec references
Options considered: A, B, C (with honest cons)
Decision:
Consequences: positive, negative, follow-ups
Evidence: spike ID, benchmark, links
Revisit when:
```

ADR files live in `docs/adr/NNN-title.md` and are created as each is decided; this index is the single list.
