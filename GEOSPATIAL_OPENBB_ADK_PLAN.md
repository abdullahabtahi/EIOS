# EIOS Architecture & Sprint Plan: Governed Geospatial Intelligence, Real-World Data Layer, MCP & Google ADK

**Version**: `2.0.0` (supersedes `1.0.0`, an unvalidated first draft)
**Date**: `2026-10-13`
**Status**: `DRAFT FOR REVIEW. No specs, ADRs or code have been written.`
**Change basis**: independent research plus a read-only spike on 2026-10-13 (section 2). Every claim not verified is tagged `[SPIKE]` and listed in section 11.
**Governance**: `CLAUDE.md` constitutional invariants RL-1..RL-7 and the provenance regime apply to everything below.

---

## 1. Thesis

### 1.1 What we are building
Not a CARTO clone. CARTO sells ungoverned agentic GIS. EIOS's edge is that **the map is a view over ontology objects**, every number is gated by the Metric Auditor, and every consequential action ends as a KMS-signed four-eyes intent in a WORM ledger. That is the Palantir pattern (ontology plus actions), delivered with QuantumBlack-style measured rigor (evals on real labels) on a Google Cloud serverless stack.

### 1.2 Flagship: "Follow the Money"
An AML analyst opens a case and asks: *"Where does this ring's money end up, and who really owns it?"*
1. The agent's plan streams as a **glass-box timeline** (live ADK events).
2. It pulls counterparties through OMCP, resolves them against open entity data (entity resolution, an existing L1 service), and screens sanctions.
3. It traverses ownership and offshore-structure graphs, then geocodes and routes through MCP tools.
4. Arcs animate hop by hop on a Google Maps and deck.gl canvas to jurisdictions. Every datum is clickable to its source, licence and as-of date.
5. The SAR draft cites every datum. The Auditor Gate blocks any number a tool did not produce.
6. The analyst stages a freeze, which goes to KMS signing, four-eyes approval and the WORM ledger.
7. Each answer carries a **proof bundle** (query hashes, BigQuery snapshot reference, signature) that replays exactly later.

Supporting scenarios, in order: partner churn cohorts by region (the churn brief asks for region/segment systemic risk) and macro/competitor shock into the causal DAG.

### 1.3 Scoring alignment (AI Builder Cup)
| Criterion | Weight | How this plan earns it |
|---|---|---|
| Technical merit and Gen AI | 40% | ADK multi-agent mesh; MCP consumed and exposed; typed `SpatialIntent` compiled deterministically (no free-form LLM math); measured evals on real labels; serverless Cloud Run scale-out |
| Problem alignment | 25% | BFSI theme: AML, fraud, partner risk, all in the briefs |
| Innovation | 25% | Governed agentic GIS, proof-carrying answers, structural precedent search over real offshore data |
| UX and solution design | 10% | Glass-box timeline, map as ontology lens, existing cockpit shell |

Required platform fit: Gemini plus deployment on Cloud Run. Both are native here.

---

## 2. Spike Findings (2026-10-13, read-only)

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| F1 | `gemini-3.8-flash` works on this project at location **`global`**, returns **404 in `us-central1`** `[SPIKE]` | direct `generateContent` calls | The gateway defaults to `us-central1` in `llm_gateway/providers/gemini_client.py:14` and `vertex.py:16`, so live calls fail unless `GOOGLE_CLOUD_LOCATION=global`. The synthesis node swallows exceptions, so the failure is invisible. **Fix first** (item P1-1). |
| F2 | ICIJ Offshore Leaks latest dump: 72 MB zip, dated 2026-09-09 `[SPIKE]` | HTTP headers, download | Fetchable by a scheduled job |
| F3 | Scale: 814,344 entities, 771,369 officers, 26,775 intermediaries, 402,321 addresses, 3,339,272 relationships `[SPIKE]` | file profile | In-memory NetworkX is no longer honest at this size, which justifies a graph backend |
| F4 | Top entity jurisdictions: Bahamas 209,713; BVI 172,389; Malta 83,939; Nevis 70,604; Aruba 49,050; Panama 48,691 `[SPIKE]` | file profile | Real jurisdiction-risk context for the map |
| F5 | Relationship types: `officer_of` 1.72M, `registered_address` 833k, `intermediary_of` 599k, plus `same_name_as`, `similar`, `same_as` `[SPIKE]` | file profile | The `same_*` edges are ICIJ's own entity-resolution hints |
| F6 | Every row carries `sourceID` (Panama Papers, Paradise Papers, Bahamas Leaks and so on) `[SPIKE]` | file profile | Native provenance per row |
| F7 | ICIJ licence: ODbL database, CC BY-SA contents; share-alike applies to derived databases `[SPIKE]` | ICIJ pages and a mirror | Attribution and non-implication disclaimer required in UI |
| F8 | OpenSanctions bulk: CC BY-NC; any for-profit use or self-hosted screening needs a licence `[SPIKE]` | OpenSanctions docs | Hackathon use is fine; the production design uses a pluggable screening port |
| F9 | OpenBB ODP is AGPL; unmodified internal use needs no release, modified network services do `[SPIKE]` | OpenBB FAQ | Run unmodified in an isolated service |
| F10 | `openbb-mcp-server` exists (`openbb-mcp`, streamable HTTP, exposes GET endpoints as tools) `[SPIKE]` | OpenBB docs | Consume it as an MCP tool source |
| F11 | Google managed MCP endpoints: `bigquery.googleapis.com/mcp`, `mapstools.googleapis.com/mcp` (Maps Grounding Lite); BigQuery is labelled "Preview" in one snapshot `[SPIKE]` | Google supported-products page | Treat as preview: wrap behind our own tool port |
| F12 | Dekart is AGPLv3 (one mirror says MIT) `[SPIKE]` | repo page | Reference only, never embedded |
| F13 | Google Isochrones API exists (separate service, 1 hour drive cap, pre-GA at launch) `[SPIKE]` | Google docs | Use for catchments if needed |

Not verified: GLEIF terms (the official page links to separate Terms of Use), Elliptic licence, native H3 in BigQuery, BigQuery Graph and Spanner Graph feature parity, GDELT availability.

---

## 3. Product & UX Design

### 3.1 Placement
A first-class destination in `<AppNavRail />` (the "Geospatial" item currently shows `SOON`), not a sub-tab of a workstation. Scenario views federate back into the AML, Partner and Executive workstations afterwards.

### 3.2 Hard constraints from `EIOS/web-prototype/CLAUDE.md`
- **Light mode on analytical surfaces.** The map must use a light Google Maps style. The v1.0.0 plan's "Carto Dark Matter" basemap violates this rule.
- **Strict 2-header maximum**, no third toolbar. The agent panel and layer palette are floating overlays, not headers.
- Text floor 11px; `cx-*` tokens; provenance tag on every figure.

### 3.3 Interaction model
- **Map as ontology lens.** Clicking any mark opens the existing Entity 360 inspector, not a bespoke popup.
- **Glass-box timeline.** Plan, tool calls, tool results and auditor verdicts stream live; the GeoSQL/tool trace is expandable.
- **Proof chip** on every answer: opens the evidence bundle and offers "replay".
- **Governed action shelf** (existing) receives staged intents; the map never mutates state.
- **Honest degradation.** A network partition shows `[REPLAY]` with the as-of time (RL-7).

---

## 4. Data Architecture

### 4.1 Two-layer data policy
- **Real world layer** (open data, governed products): offshore structures, corporate ownership, sanctions, geography, macro, competitor markets.
- **Client private layer** (synthetic, tagged `[ILLUSTRATIVE]`): accounts, partners, IPs, devices. This is how an FDE engagement works, because a client's private data is never open.

### 4.2 Source register
| Product | Source | Licence | Use | Status |
|---|---|---|---|---|
| `offshore_structures` | ICIJ Offshore Leaks | ODbL + CC BY-SA | Jurisdiction risk, structural precedent search | Spiked |
| `corporate_ownership` | GLEIF Level 2 | verify | Who-owns-whom (accounting consolidation, not beneficial ownership) | Open |
| `sanctions` | OpenSanctions (demo), official lists (production default) | CC BY-NC (demo) | Screening port | Spiked |
| `illicit_graph_benchmark` | Elliptic1 / Elliptic++ (about 204k transactions, about 2% illicit) | verify | Detector benchmark on real labels | Open |
| `geo_reference` | Overture Maps (BigQuery public dataset) | open | Divisions, places | Located |
| `macro_market` | FRED, OpenBB (competitor equities) | public / AGPL | `MacroEvent`, `competitor_benchmarks` | Spiked |

### 4.3 Policies
- **P-1: no synthetic assertion about a real-named entity.** Fictional cases link to synthetic shell entities and to *jurisdictions* and *service-provider archetypes*, never to real named companies.
- **P-2: entity-level and jurisdiction-level only.** No natural-person names or street-level geocoding from ICIJ.
- **P-3: provenance on every row.** Source, licence, as-of date and a new tag `[EXTERNAL]` (to be decided in an ADR).
- **P-4: UI disclaimer.** ICIJ's non-implication notice and attribution shown wherever its data appears.

### 4.4 Structural precedent search
Deterministic subgraph-pattern matching (for example, a jurisdiction chain of length 3 with shared intermediary) against the real offshore graph returns counts and anonymized precedents. The LLM only narrates the result (RL-1).

### 4.5 Pipeline
Cloud Run Jobs (Cloud Scheduler) fetch, validate against a Pydantic contract, write Parquet to GCS, load to BigQuery. H3 indexes are computed in the job with the `h3` library, which avoids depending on unverified native BigQuery H3. Failures go to the existing DLQ path.

---

## 5. Ontology Extensions

| Kind | Additions |
|---|---|
| Object types | `Jurisdiction`, `OffshoreEntity` (reference), `Place`, `ShellEntity` (synthetic), `Corridor` (derived) |
| Link types | `IncorporatedIn`, `RegisteredAt`, `ControlledBy`, `FlowsTo` (geo-annotated), `ResolvesTo` (entity resolution, with match score) |
| Action types | `StageAccountFreeze`, `StageCorridorReview`, `ProposeFeeCorridorShift`, all intent-only |
| Properties | `geo` (point or region reference), `h3_r8`, `provenance` |

The geo-metric registry sits beside the existing DuckDB/BigQuery metric registry: named, versioned, parameterized spatial metrics. The agent selects metrics; it never writes the math.

---

## 6. Agent Architecture (Google ADK + MCP)

### 6.1 Mesh
ADK 2.0 on Cloud Run (pinned; 2.0 has breaking changes from 1.x). A coordinator delegates to specialists: the five existing ones, plus `GeospatialSpecialist` and `MacroMarketSpecialist`. The ADR-016 blackboard semantics and the 3-cycle bound carry over. Sessions use Firestore (already an optional dependency).

### 6.2 Typed intent, deterministic compile
Gemini emits a structured `SpatialIntent` (metric, filters, geometry, grouping). A deterministic compiler produces parameterized BigQuery SQL from the geo-metric registry. A free-form explore mode exists but passes an allowlist validator, a dry-run and a bytes-billed cap. This satisfies RL-1 by construction.

### 6.3 MCP, both directions
- **Consume:** BigQuery MCP, Maps Grounding Lite MCP, `openbb-mcp-server`, all wrapped behind our own tool port so a preview-status change never breaks the agent.
- **Expose:** OMCP as an MCP server, so external agents query the governed ontology with the same markings and Auditor.
- **Untrusted text:** all third-party tool output goes through `common/untrusted_text.py`; Model Armor is evaluated as a managed layer on top.

### 6.4 Callbacks replacing LangGraph logic
- Auditor egress scan on every response (today `egress_firewall`).
- Compliance-hold arbitration (today in `supervisor_node`).
- HITL interception: any mutation call yields an `ActionIntentToken` signed with Cloud KMS ECDSA P-256 and routed to the governed shelf (replaces `interrupt`).
- Exceptions surface as typed errors with a labelled fallback, never canned text.

### 6.5 Gateway
Keep `llm_gateway/` (prompt lock, replay cache, caps). Fix the location default (F1). Use Gemini context caching for the long ontology and policy prefix. Record per-turn latency, tokens and cost in OTel.

---

## 7. GCP Serverless Topology

```
Browser ── Next.js (Cloud Run) ── deck.gl on Google Maps
              │ REST + SSE
   ┌──────────▼──────────┐   ┌───────────────────┐   ┌──────────────────┐
   │ cockpit-api (FastAPI)│──▶│ agent-mesh (ADK)  │──▶│ Vertex Gemini     │
   │ existing, split into │   │ MCP clients+server│   │ (location=global) │
   │ routers              │   └─────────┬─────────┘   └──────────────────┘
   └──────────┬───────────┘             │ MCP / OMCP
              │                 ┌───────▼────────┐  ┌──────────────────────┐
              │                 │ geo-api        │  │ market-data (OpenBB, │
              │                 │ H3 aggregates  │  │ isolated, unmodified)│
              │                 └───────┬────────┘  └──────────┬───────────┘
   ┌──────────▼───────────────────────▼──────────────────────▼───────────┐
   │ BigQuery (system of record, snapshots) │ GCS Parquet │ Firestore      │
   │ graph backend (decision D-2)           │ Cloud KMS   │ Secret Manager │
   └──────────────▲───────────────────────────────────────────────────────┘
        Cloud Run Jobs + Scheduler (open-data ingestion) ── Pub/Sub ── DLQ
```

- **Statelessness.** The DuckDB hot state and NetworkX graph are single-instance today. Readers warm-start from GCS Parquet snapshots; BigQuery serves analytics. Min-instances is set only where a warm start matters.
- **IaC.** Extend the existing `infra/modules/run_service`; the `infra_policy` gate enforces least-privilege identities.
- **Observability.** Existing OTel into Cloud Trace and Logging.
- **Targets** (all `[TARGET]`, to be validated in load tests): p95 spatial aggregate under 1s for pre-aggregated H3 views; agent first-token under 2s.

---

## 8. Red-Line Mapping

| Rule | How satisfied | Proof |
|---|---|---|
| RL-1 | `SpatialIntent` compiles to registered metrics; free-form SQL gated; Auditor egress | hallucination eval over geo dialogs |
| RL-2 | Mutations only as KMS-signed four-eyes intents | static check plus runtime deny test |
| RL-3 | Macro and corridor causal claims pass the evidence gate or show "Correlation Only" | existing refuter tests extended |
| RL-4 | CGNAT hub suppression applies to geo-clustered IP rings | existing detector tests plus geo fixtures |
| RL-5 | Proof bundle references the ledger sequence | chain verification test |
| RL-6 | What-if over regional macro shocks under 200ms `[TARGET]`, attribution sums to 100% | perf plus invariant test |
| RL-7 | `[REPLAY]` fallback for MCP, OpenBB and map failures | partition simulation test |

---

## 9. Evaluation Plan

- **Real-label benchmark** (Elliptic, once licence confirmed): mule-ring and graph detectors against baselines, reported as `[MEASURED]` in CI.
- **Hallucination and citation evals** over geo dialogs: 100% of numbers match tool outputs, extending `evals/suites/redlines`.
- **Golden dialogs** for the three scenarios, including adversarial prompt-injection through MCP output.
- **Agent trajectory evals**: correct tool order, bounded cycles, correct refusal when a tool is unavailable.
- **Load tests** for `geo-api` and agent turns, producing the `[TARGET]` validations above.

---

## 10. Sprint Plan

No dates; each phase has an exit criterion. Spec-kit order applies: specs 021 (ADK migration), 022 (geospatial), 023 (open data and market) and the ADRs come first.

### Phase 0: Decisions and documents
- Register open decisions in `config/open_decisions.yaml` (D-1..D-6 below) so `open_decision_check` passes.
- ADRs: supersede 016 for ADK; geo stack; `[EXTERNAL]` provenance tag; open-data licensing; graph backend.
- **Exit:** specs and ADRs reviewed; `make check` green.

### Phase 1: Foundations
| ID | Item | Size |
|---|---|---|
| P1-1 | Fix gateway location default and stop swallowing LLM exceptions; add a live-call smoke test behind `requires_cloud` | S |
| P1-2 | ADK migration with behavioral parity against current LangGraph tests; callbacks per 6.4 | L |
| P1-3 | Real tool-calling loop for existing specialists (replace keyword routing) | M |
| P1-4 | Trajectory and hallucination eval suites in the harness | M |

**Exit:** parity tests green; live Gemini turn verified; evals gating in CI.

### Phase 2: Real-world data layer (parallel with phase 3)
| ID | Item | Size |
|---|---|---|
| P2-1 | Ingestion jobs and contracts for ICIJ and geo reference; provenance columns; H3 indexing | M |
| P2-2 | Graph backend per D-2, with structural precedent search | L |
| P2-3 | Entity resolution of synthetic counterparties to jurisdictions and archetypes | M |
| P2-4 | Sanctions screening port with demo adapter | S |
| P2-5 | `market-data` service wrapping OpenBB (isolated) with replay cache | M |

**Exit:** data products pass contracts; precedent query returns deterministic results under load targets.

### Phase 3: Geospatial experience (parallel with phase 2, contract-first with a `mock-geospatial.ts`)
| ID | Item | Size |
|---|---|---|
| P3-1 | Activate Geospatial nav item and route | S |
| P3-2 | deck.gl on Google Maps canvas, light style | M |
| P3-3 | Glass-box timeline and proof chip | M |
| P3-4 | Layer palette and viewport-reactive widgets | M |
| P3-5 | `geo-api` aggregates and geo-metric registry | M |

**Exit:** flagship flow works end to end against fixtures.

### Phase 4: Integration and scenarios
- Flagship "Follow the Money" end to end with real data layer, MCP tools and signed intent.
- Churn cohort scenario and macro shock scenario.
- OMCP exposed as MCP server with a demo external agent.

**Exit:** golden dialogs green; proof-bundle replay verified.

### Phase 5: Hardening
Load tests, cost model update (`docs/cost_model.csv`), runbooks, security review, demo video, proposal deck.

---

## 11. Open Decisions and Risks

| ID | Decision | Recommendation |
|---|---|---|
| D-1 | Natural persons from ICIJ | Excluded (decided 2026-10-13) |
| D-2 | Graph backend: BigQuery Graph vs Spanner Graph vs both `[SPIKE]` | Spike both on the ICIJ data; default to BigQuery for analytics |
| D-3 | Elliptic and GLEIF licences | Verify before ingestion; drop Elliptic from CI if unclear |
| D-4 | `[EXTERNAL]` provenance tag | Add via ADR |
| D-5 | Managed MCP servers are preview | Wrap behind our tool port |
| D-6 | Maps API key and billing | Use project credits; key restricted by referrer |

| Risk | Mitigation |
|---|---|
| Python 3.14 compatibility of `google-adk` and `openbb-core` `[SPIKE]` | Isolate in separate services with their own runtimes |
| AGPL obligations | Run OpenBB unmodified in its own service; no modifications |
| Real-person harm from real data | Policies P-1..P-4 |
| Scope growth | Flagship first; churn and macro scenarios cut before the flagship slips |
| ADK 2.0 session-schema churn | Pin version; parity tests |

Spikes still to run: GLEIF terms and sample, Elliptic licence, native H3 in BigQuery, graph backend benchmark, managed MCP stage check.

---

## 12. Sources
[ICIJ Offshore Leaks](https://offshoreleaks.icij.org) · [OpenSanctions licensing](https://www.opensanctions.org/docs/commercial/exemption/) · [OpenBB licence FAQ](https://docs.openbb.co/odp/python/faqs/license) · [OpenBB MCP](https://docs.openbb.co/odp/python/quickstart/mcp) · [Google MCP supported products](https://docs.cloud.google.com/mcp/supported-products) · [ADK 2.0](https://cdn.jsdelivr.net/gh/google/adk-python@main/README.md) · [Overture on BigQuery](https://docs.overturemaps.org/getting-data/data-mirrors/bigquery/) · [Dekart](https://github.com/dekart-xyz/dekart) · [Google Isochrones API](https://developers.google.com/maps/documentation/isochrones/key-concepts) · [AI Builder Cup themes](https://aibuildercup.com/themes.html)
