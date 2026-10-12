# Enterprise Intelligence Operating System (EIOS) — Master Specification v3
## Forward-Deployed Engineering Engagement: POC → Production (Simulated)

**Status:** v3 — supersedes v2 (archived at `docs/archive/initial_plan_v2.md`). Change rationale: `docs/red_team_findings_v3.md`.
**Framing:** This is an institutional forward-deployed-engineering (FDE) engagement for an enterprise online brokerage platform. We treat operational briefs as enterprise problem statements and run the engagement with rigorous institutional discipline: discovery → POC → hardening → production readiness → handoff. All data is synthetic. The output is a working system **and** a portfolio-grade evidence trail (ADRs, eval reports, runbooks, case study).
**Lens:** AI-native agentic platform architecture × Enterprise Ontology doctrine × Cloud reference architecture.

**Companion documents (read together; this file is the index and the invariants):**

| Doc | Purpose |
|---|---|
| `docs/engagement_plan.md` | Phases, exit criteria, SLOs, environments, CI/CD/IaC, cost model, runbooks, rollout/adoption, risk register, portfolio artifacts |
| `docs/models_and_evals.md` | Concrete models per capability, baselines to beat, metrics/targets, eval harness, Red-Line tests |
| `docs/data_products_and_omcp.md` | Data-product catalog, Ontology object/link/action types, OMCP tool contracts |
| `docs/synthetic_data_strategy.md` | Layer 0 generators: hard negatives, sealed holdout typologies, seeds |
| `FEIOS/docs/spikes_and_adrs.md` | Unverified stack pins as time-boxed spikes; ADR index |
| `docs/red_team_findings_v3.md` | v2→v3 change log |
| `docs/brief/*` | **Client briefs — primary ground truth** (`data.md`, `monitoring.md`, `fraud`, `churn`) |
| `docs/foundry.md`, `docs/architecture.md` | Reference doctrine |

---

## 0. How to read this spec

### 0.1 Source-of-truth hierarchy
1. `docs/brief/*` — the client's stated problems and "blow our minds" bar.
2. This document and its companions — the design responding to them.
3. Reference doctrine (`foundry.md`, Rewired skill) — patterns we borrow, not requirements.
4. **Not authoritative:** `FEIOS/`, `DESIGN_PLAN.md`, `DESIGN.MD`. These are an early *external-facing website prototype*, not the platform. They will be re-derived from §7 later. Nothing in this spec bends to them, and the frontend stack is an open decision (ADR-009).

### 0.2 Labelling convention (mandatory for every number and named example)
| Tag | Meaning |
|---|---|
| `[BRIEF]` | Stated in `docs/brief/*`. Cite file. |
| `[ASSUMPTION]` | Engagement assumption we chose; must be revisitable. |
| `[ILLUSTRATIVE]` | Example output of a seeded generator. Never a claim about a real company. |
| `[TARGET]` | Acceptance threshold we commit to measuring. |
| `[SPIKE]` | Unverified technical claim; resolved by a spike in `FEIOS/docs/spikes_and_adrs.md` before anything depends on it. |

**Rule:** any figure in a UI, dossier, README or case study must trace to (a) a `[BRIEF]` citation, or (b) a generator run at a stated seed plus git SHA, or (c) an eval-harness report. v2's unsourced figures (unsourced scale claims, "5x recruiting cost", "80% of volumes", Amy's stats, third-party case-study percentages, CR84920, AP-1029, Boom 1000, named poachers) are removed or demoted to `[ILLUSTRATIVE]` scenario data.

---

## 1. Engagement framing

### 1.1 The client problem (from briefs)
Enterprise data lives in silos (CRM, ERP, partner tracking, competitive intel); executives triangulate for days from stale reports `[BRIEF data.md]`. Three operational pains sit on top:
- **A. Client monitoring / AML** — ~2,000 alerts/week, ~95% false positives, 5+ systems to pull context from `[BRIEF monitoring.md]`.
- **B. Partner/affiliate fraud** — 5,000 affiliates; opposite/mirror trading, bonus abuse, commission fraud, client recycling, traffic/bot fraud `[BRIEF fraud]`.
- **C. Partner churn** — silent disengagement across behavioural, communication, relationship, financial, competitive signals `[BRIEF churn]`.

### 1.2 Engagement thesis
One shared **Kinetic Ontology** over six domains (Client, Financial, Partner, Operational, Competitive, Compliance/Risk), hosting three operational modules (A, B, C) and a fourth capability that is the platform's organising promise: the **Executive Synthesis Engine** — cross-domain causal narrative, forecasting with driver attribution, scenario simulation, proactive briefing, conversational drill-down `[BRIEF data.md "Blow our minds"]`.

### 1.3 Personas (discovery artefacts; simulated stakeholders)
| Persona | Primary need | Surface |
|---|---|---|
| CEO / COO | "What changed overnight, why, what should I do?" | Morning Briefing, causal chain, what-if |
| CFO / Finance lead | Forecast, variance drivers, margin | Forecast + attribution view, chat |
| MLRO / Compliance head | Regulator-ready evidence, SAR quality, audit trail | Case dossier, SAR draft, ledger |
| AML investigator | 2,000 alerts → prioritised cases in seconds | Alert queue, dossier, graph |
| Head of Partnerships / partner manager | Which partners are drifting/defrauding, what to do | Churn radar, integrity cases, playbooks |
| Data platform lead | Trust in numbers, contract breaches | Data-quality board, lineage |
| CISO / Risk | No autonomous mutation, auditability | Approval + ledger + access views |

### 1.4 Success criteria (engagement level, all `[TARGET]`; per-model targets in `docs/models_and_evals.md`)
- **Zero metric hallucination:** 100% of numbers in agent output match Semantic Layer values in the eval harness (blocking CI gate).
- **Citation coverage:** 100% of assertions cite an Ontology entity ID or Data Product + as-of timestamp.
- **Module A:** beat the baseline rules engine on precision@k at equal recall on the sealed holdout; reduce a 2,000-alert weekly synthetic queue to ≤ 50 high-confidence cases without losing planted true positives `[BRIEF target; TARGET numbers ours]`.
- **Executive Synthesis:** recover the planted 4-domain causal chain, reject planted placebo edges, and attribute a forecast miss to drivers summing to 100%.
- **Operability:** SLOs in `docs/engagement_plan.md` met in a 7-day soak; all runbooks exercised once.

### 1.5 Scope
**In:** synthetic-data foundry; ingestion with contracts; ontology + metrics + graph; multi-agent mesh; cockpit; governed actions with simulated write-back; eval harness; IaC/CI-CD; observability; runbooks; case study.
**Out:** live production data/systems, live regulatory filing, production KYC vendors, mobile, multi-region active-active.

---

## 2. Requirement traceability (brief → capability → slice)

Slices are defined in §8. "Eval" points to `docs/models_and_evals.md`.

| Brief requirement | Source | Capability | Slice | Eval |
|---|---|---|---|---|
| Unified real-time ingestion, entity resolution, data-quality flags, history | data.md §1 | L1 contracts + entity-resolution service + DQ board | S0/S1 | Contract breach tests; ER precision/recall on seeded duplicates |
| Cross-domain correlation & causal analysis | data.md §2 | Synthesis Engine + causal engine | S1 | Planted-chain recovery; placebo-edge rejection |
| Forecasting, sensitivity, early warning | data.md §3 | Forecast service + driver attribution | S1 | Beats seasonal-naive; attribution sums to 100% |
| Scenario simulation | data.md §3 | Shock-injection on cached SCM | S1 | Directional correctness vs. generator ground truth |
| NL + follow-ups + challenge assumptions | data.md §4 | Conversational analytics (session memory, tool-grounded) | S1 | Multi-turn golden dialogues |
| Recommendations, impact, trade-offs, confidence, decision tracking | data.md §5 | Recommendation composer + Decision Ledger flywheel | S1/S5 | Trade-off schema completeness; flywheel recalibration test |
| Proactive briefing | data.md | Morning Briefing job | S1 | Briefing golden; timing SLO |
| Different UIs for CEO / analyst / operator | data.md Qs | Persona-specific views (§7) | S1–S4 | Persona UAT scripts |
| Alert triage 2,000→50, contextual scoring incl. KYC | monitoring.md | A: alert scorer + context assembly | S4 | Precision@k vs baseline |
| Graph rings (IP/device/card/timing) & "47 linked accounts" | monitoring.md | A: graph engine w/ hub suppression | S4 | Ring recall; hub false-merge rate |
| Round-trip laundering ($500 → 10 min → $0.01 → withdraw) | monitoring.md | A: round-trip typology detector | S4 | Recall on planted + baseline gap |
| Unsupervised new typologies | monitoring.md | A: anomaly + cluster novelty | S4 | Sealed-holdout typology detection |
| Learning from analyst decisions | monitoring.md | A: label feedback → retrain (batch) | S4/S5 | Uplift after simulated feedback |
| Real-time withdrawal intervention | monitoring.md | A: pre-withdrawal risk hold (proposal only) | S4 | p95 decision latency `[TARGET]` |
| SAR draft, near-final | monitoring.md | A: SAR composer w/ templates | S4 | Checklist completeness; citation coverage |
| Cold start; legit high-volume traders | monitoring.md Qs | A: peer-group baselines; hard negatives | S4 | Hard-negative FPR |
| Explain networks to non-technical officers | monitoring.md Qs | Narrative + graph view | S4 | Officer comprehension rubric |
| Opposite/mirror trading, timing correlation ("47 / 23 / 89%") | fraud | B: pair detector | S3 | Precision/recall vs rule baseline |
| Multi-tier sub-affiliate ring, master-partner attribution (3 layers) | fraud | B: referral-tree attribution | S3 | Ring + master recovery |
| Bonus abuse, client quality, commission fraud | fraud | B: abuse & quality scoring | S3 | PR-AUC |
| **Client recycling, bot/traffic fraud, impossible conversion rates ("12 partners")** | fraud | B: recycling detector; traffic anomaly | S3 | Planted-pattern recall |
| Explainable, evidence-based, human in the loop | fraud | Dossier + Action Intent Token | S3 | Approval-path tests |
| Proactive discovery/learning | fraud | B: emerging-pattern miner | S3 | Sealed-holdout |
| Multi-signal churn, High/Med/Low, explainable | churn | C: hazard model | S2 | AUROC/PR-AUC/calibration |
| Dip vs disengagement; prediction window; sens vs spec | churn | C: change-point + window analysis | S2 | Lead time curve; threshold trade-off report |
| Value × risk prioritisation | churn | C: priority = P(churn) × value at risk | S2 | Top-k value captured |
| Region/segment cohort systemic risk | churn | C: cohort detector | S2 | Planted cohort recall |
| Learn which interventions work; proactive playbooks | churn | C: intervention uplift + playbook recs | S2/S5 | Uplift estimator on simulated outcomes |

---

## 3. Architecture

### 3.1 Design invariants (non-negotiable; each has a test)
1. **LLMs never compute business metrics.** All numbers arrive via deterministic tool calls to the Semantic Metric Layer. A **Metric Auditor Gate** rejects any response containing a business metric not present in tool outputs. Statutory, regulatory, and legal citations (e.g. `Section 314(b)`, `31 CFR 1010`, `Form 111`) are normalized and exempted to eliminate false-positive auditor rejections on regulatory compliance narratives. *(Test: adversarial prompts; hallucination eval; legal citation normalizer tests.)*
2. **No God Agent.** Specialist agents per domain behind one Supervisory Router; each agent has an explicit tool allow-list.
3. **Batch and streaming decoupled.** Streaming path (ingest → contract → hot state) never blocks on batch (feature materialisation, training, SCM fitting).
4. **SCMs are precomputed offline.** Causal structure and refutations are computed in batch and cached with a version; live turns do fast parametric inference only. *(Correction: DoWhy refutation is not sub-second; v2 implied it was.)*
5. **No autonomous write-back.** Every mutation is an *Action Intent* → human approval → execution against a **simulated write-back sink**. No direct-write path exists in code. *(Test: static check + runtime deny.)*
6. **Data as a Product.** Agents and cockpit consume data products through contracts, never raw tables.
7. **Honest uncertainty.** Causal claims require passing the causal-evidence gate (§5.1); otherwise the agent must say "correlation detected; insufficient evidence for causation."
8. **Deterministic fallback.** Every critical path has a cached/replayable fallback that is clearly labelled as such in the UI.

### 3.2 Layered topology (6 layers, unchanged in shape; contents corrected)

```
L4  Cockpit (persona views, chat, graph, approvals)     ── GraphQL + SSE ──┐
L3  Reasoning mesh: Coordinator (Blackboard) → domain   ── OMCP tools ─────┤
    agents + Synthesis + Causal engine + Auditor Gate                      │
L2  ONTOLOGY API = Data + Logic + Action + Security                         │
    ├ Metric layer (DuckDB registry) ├ Property graph (NetworkX + Hubs)     │
    └ Object/Link/Action types, Functions, Markings/RBAC                    │
L1  Ingestion spine: Pub/Sub → contract validator → hot state (DuckDB) +    │
    raw store (BigQuery + GCS Parquet); DLQ; Tiered Compactor; ER; DQ       │
L0  Synthetic Enterprise Data Foundry (seeded; hard negatives; sealed holdout)
L5  Governed actions: Action Intent Tokens (KMS-signed) → approval service →
    simulated write-back sink → append-only Decision Ledger + outcome flywheel
```

**Tier mapping (Rewired skill):** L1–L2 ≈ Tier 1–2; L3 ≈ Tier 3; L4–L5 ≈ Tier 4.

### 3.3 Layer specifications (concise; details in companions)

**L0 — Synthetic Enterprise Data Foundry.** Seeded per-domain generators (client, partner, financial, competitive, operational, **AML/transactions**) writing to the same Pub/Sub topics a real feed would use. Requirements added in v3: **hard negatives** (legit high-volume traders, shared office/café/CGNAT IPs, families sharing a device, seasonal/holiday login dips, unrelated fee changes), **sealed holdout typologies** the model developer never sees, **label noise**, and **placebo edges** with zero true causal effect. See `docs/synthetic_data_strategy.md`.

**L1 — Ingestion & contract spine.** Pub/Sub → Cloud Run worker (FastAPI). Pydantic contracts per data product; breach → dead-letter + alert + degrade gracefully (freshness banner), never silent drop. Hot state in DuckDB with a **warm-start** procedure (rehydrate from Parquet snapshot on cold start; min-instances=1 in prod-like env). A **Tiered Compaction Strategy** rolls hourly Parquet deltas into compacted daily baselines, guaranteeing cold-boot rehydration stays strictly under the $< 1.5\text{s}$ SLA regardless of ingestion history. Entity-resolution service (deterministic keys + probabilistic match) links the same client/partner across sources and assigns a pseudonymized Identity Cluster Key (`tok_id_cluster_<hex16>`); a **Data-Quality board** exposes contract breaches, ER conflicts and freshness `[BRIEF data.md §1]`.

**L2 — Ontology & Semantic Layer.**
- *Ontology* = object types, link types, action types, functions, security markings (four-fold; "the Ontology is not a semantic layer" — `foundry.md`).
- *Metric layer:* governed KPI registry (definition, grain, owner, version) implemented via an in-process DuckDB Semantic Registry (ADR-003). Guarantees sub-5ms deterministic SQL aggregations with zero Node/CubeStore operational overhead.
- *Graph:* NetworkX in-memory property graph, rebuilt from snapshot on warm start; Louvain/connected components with **hub suppression** (penalizing high-degree CGNAT / hosting IPs) to avoid merging via shared office IPs (ADR-004). Scale ceiling documented; Spanner Graph/Neo4j listed as the production alternative.

**L3 — Reasoning mesh.** LangGraph on Cloud Run organized as a **Multi-Agent Shared Blackboard Architecture with an Arbitrating Coordinator Agent** (ADR-016).
- The Coordinator maintains shared session hypotheses, routes sub-goals to domain specialists ({Client, Financial, Partner, Operational, Competitive, Compliance, Sentinel-AML, Synthesis, Scenario, Briefing}), and reconciles conflicting propositions (e.g. Partner Manager proposing retention while AML Sentinel proposes account freeze).
- All multi-agent deliberation cycles are strictly bounded to a **maximum of 3 reflection cycles** to prevent infinite agent oscillation and guarantee p95 turn latency $< 3.5\text{s}$.
- All agent interactions with domain data go through typed **OMCP tools** (`docs/data_products_and_omcp.md`). LLM access goes through a thin provider-agnostic gateway; model IDs, pricing and caching behaviour are **config, verified in spike S-01**. Session memory supports follow-ups and assumption challenges.

**L4 — Cockpit.** Persona-based views, chat, graph, approvals, DQ board (see §7). API surface: current lean is GraphQL for queries plus SSE for streaming agent output, but this is open until ADR-014 (with ADR-009) is decided. Frontend framework/design system: ADR-009 (open; the `FEIOS/` scaffold is a website prototype, not a constraint).

**L5 — Governed actions & ledger.** See §6.

---

## 4. Ontology & data products (summary)
Full catalog in `docs/data_products_and_omcp.md`. Data products (owners are persona roles, contracts + SLAs defined): `client_360`, `client_funnel`, `transactions_aml`, `trading_activity`, `device_network_graph`, `partner_360`, `partner_referral_tree`, `commission_ledger`, `partner_engagement_signals`, `partner_comms`, `financial_pnl`, `competitor_benchmarks`, `platform_operations`, `compliance_cases`, `decision_ledger`. Core object types: `ClientAccount, Device, IPAddress, PaymentMethod, Partner, SubAffiliate, Competitor, Product, Region, Case, Alert, Decision, MacroEvent`. Action types: `FreezeAccount, HoldWithdrawal, ClawbackCommission, SuspendPartner, LaunchRetentionPlaybook, EscalateToMLRO, FileSARDraft`.

---

## 5. Capability specifications

Each capability lists: brief requirements → approach → acceptance → fallback. Model details and metrics: `docs/models_and_evals.md`.

### 5.1 Executive Synthesis Engine (Slice S1 — highest priority)

**Requirements `[BRIEF data.md]`:** true cross-domain chain (Competitive → Partner → Client → Financial); predictive early warning with root-cause split; scenario simulation; proactive morning briefing; natural conversation with follow-ups; learning from decisions; trade-off and confidence presentation.

**Approach**
1. **Causal DAG** authored from domain knowledge, edges tagged with rationale. Structural equations fitted on synthetic history in batch. DAG versioned.
2. **Causal-evidence gate (corrected):** an edge may be asserted as causal only if (a) the estimated effect's confidence interval excludes zero, (b) the **placebo-treatment** refuter yields an effect not distinguishable from zero (i.e. *p > 0.05 on the placebo is the passing result*), (c) random-common-cause and data-subset refuters leave the estimate stable within a tolerance, and (d) confidence ≥ 0.80. Otherwise output "correlation detected; insufficient evidence for causation." v2 stated this backwards.
3. **Offline/online split:** nightly job fits + refutes + caches per-edge results; live path reads cache and runs parametric shock propagation (fast).
4. **Forecast:** baseline seasonal-naive; challenger gradient-boosted/regression with leading indicators; **driver attribution** by decomposition that sums to 100% (brief example: 40/35/25 competitive/partner/operational `[BRIEF data.md]`; our numbers are generated and `[ILLUSTRATIVE]`).
5. **Scenario simulation:** shock injection (e.g. competitor payout ↑, competitor acquisition) → propagated deltas with intervals, ranked defensive actions with ROI ranges and confidence.
6. **Morning Briefing:** scheduled Cloud Run job → briefing object (`n` insights, risks, opportunities) persisted, then streamed; the user can ask "elaborate" (follow-up).
7. **Recommendation composer:** each recommendation carries impact estimate, trade-offs (pros/cons), confidence, evidence citations, and links to an Action Type.
8. **Decision learning flywheel & causal weight recalibration (Doubly Robust AIPW):** To avoid "confounding by indication" (human officers only approving actions on high-risk accounts), `ActionIntentToken` records the proposing agent's propensity score $e(X) = P(\text{Action Proposed} \mid X)$ and observed causal context at proposal time (§6.1). The batch flywheel computes **Augmented Inverse Propensity Weighting (AIPW)** estimators over logged outcomes in `decision_outcomes_ledger` rather than naive observational averages, ensuring unbiased offline recalibration of SCM edge weights and intervention uplift.

**Illustrative scenario (`[ILLUSTRATIVE]`, seed in generator):** competitor raises partner payouts → our top-partner mix shifts → new-client quality falls → LTV declines. Precise numbers come from the seeded run.

**Acceptance:** planted chain recovered with correct edge ordering; ≥ 1 planted placebo edge rejected; forecast beats baseline on holdout; attribution sums to 100%; every number passes the Auditor Gate; 5-turn golden dialogues pass; AIPW estimator recovers true planted uplift on synthetic trials.
**Fallback:** cached briefing + precomputed SCM results served with a "replay" badge.

### 5.2 Module C — Partner Churn Radar (Slice S2)

**Requirements `[BRIEF churn]`:** five signal families; High/Medium/Low tiers with explanations; value × risk prioritisation; dip vs. disengagement; region/segment cohort detection; prediction-window and sensitivity/specificity trade-offs; learn which interventions work; proactive retention recommendations.

**Approach:** discrete-time hazard model over the five families (behavioural: login/referral decay; communication: ticket sentiment/unresolved; relationship: manager touchpoints; financial: commission trend; competitive: poaching-language NLP over comms). Change-point detection distinguishes seasonal dips from disengagement. Cohort detector aggregates by region/segment with statistical anomaly tests. Priority = P(disengage within window) × partner value. Retention playbooks are Action Types; outcomes logged to the ledger; intervention uplift estimated over time.

**Acceptance:** beats "no login for N days" baseline on PR-AUC and lead time; calibration within tolerance; planted cohort found; seasonal-dip hard negatives not flagged; explanation lists top contributing signals with citations.
**Fallback:** rule + z-score scorer (baseline) behind the same API.

### 5.3 Module B — Partner & Affiliate Fraud Sentinel (Slice S3)

**Requirements `[BRIEF fraud]`:** opposite/mirror trading; multi-tier ring mapping with master-partner attribution across 3 layers; bonus abuse; commission fraud; **client recycling; traffic/bot fraud; impossible conversion rates**; relationship-aware; evidence-based; human-in-the-loop; proactive pattern discovery.

**Approach:** pair-level detector over partner–client portfolios (time-overlap, direction anti-correlation, size symmetry, net P&L ≈ 0 vs. commission extracted); referral-tree attribution to master partner; bonus-abuse scorer (deposit → minimal activity → withdraw); client-quality score feeding commission decisions; recycling detector (same identity cluster key `tok_id_cluster_<hex16>` re-registered under different partners); traffic anomaly detector (click→signup→deposit conversion outliers vs. peer distributions); emerging-pattern miner (unsupervised) evaluated on sealed holdout typologies.

**Acceptance:** beats "same instrument, opposite direction within N s" rule baseline; recovers planted ring shape and master partner; legit hedgers/IB portfolios (hard negatives) not flagged above threshold; each case dossier contains evidence, confidence, and a proposed Action Intent (clawback/suspend) — never auto-executed.
**Fallback:** rule baseline + graph attribution only.

### 5.4 Module A — Client Fraud Sentinel / AML Monitoring (Slice S4)

**Requirements `[BRIEF monitoring.md]`:** per-customer behavioural anomaly; graph rings; contextual scoring incl. KYC; automated evidence collection; learn from analyst decisions; real-time withdrawal intervention; SAR drafts; 2,000 alerts → 50 high-confidence cases; unsupervised new typologies; cold start; legitimate high-volume traders; regulator-ready narratives; explain networks to non-technical officers.

**Approach:** (1) peer-group behavioural baselines (solves cold start) + per-customer anomaly; (2) supervised alert scorer trained on analyst-labelled synthetic history; (3) graph ring detector with hub suppression; (4) round-trip typology detector (deposit → short-hold micro-P&L trade → withdraw); (5) contextual features (KYC recency, "72 hours after KYC approval" pattern `[BRIEF]`); (6) evidence assembler collapsing 5+ source lookups into one dossier; (7) SAR composer (regulator-configurable template, every business metric cited from tool outputs; statutory references normalized); (8) pre-withdrawal check emitting a `HoldWithdrawal` *proposal* — a human approves; (9) analyst decisions become labels for batch retraining.

**Acceptance:** vs. baseline threshold-rules engine, higher precision@50 at equal recall on sealed holdout; hard-negative FPR bounded; SAR draft passes a completeness checklist with 100% citation coverage; dossier assembly p95 within SLO `[TARGET in engagement_plan]`.
**Fallback:** rules baseline + graph view + templated SAR.
**Note:** v2 invented details (CR84920, "<450ms", "23 accounts", jurisdiction names). The brief contains none; scenario data are now generator output, and jurisdiction templates are configurable examples.

---

## 6. Governance, security, action layer

### 6.1 Action Intent Tokens
- Agents emit an **Action Intent** (type, target IDs, parameters, evidence refs, model/prompt version, requester, `nonce`, `issued_at`, `expires_at`, optional `propensity_score` $e(X)$, `causal_context`).
- Signing: **Cloud KMS asymmetric signature (ECDSA P-256)** — provides non-repudiation, unlike v2's symmetric HMAC. Key rotation by KMS key versions; verifier checks `kid`.
- **Replay protection:** nonce + idempotency key stored in a transactional store (Firestore); tokens single-use; short expiry (`[ASSUMPTION]` 15 min).
- **Two-phase commit:** (1) propose → intent persisted, status `PENDING`; (2) authorised human approves (RBAC + optional four-eyes for high-severity) → approval record co-signed; (3) executor calls the **simulated write-back sink** (a mock core-systems API that records what *would* have happened and can fail on demand for chaos tests) → result appended to ledger.
- **State machine** lives in an approval service (Cloud Run + Firestore) — v2's Cloud Workflows is a poor fit for interactive human approval and is retained only for scheduled jobs (Briefing, nightly SCM refit).

### 6.2 Decision Ledger & Upstream Atomic Sequencer
- BigQuery is **not immutable by default**, and streaming inserts into partitioned tables are distributed and out-of-order. Controls:
  1. **Upstream Transactional Sequence Counter (ADR-017):** Prior to streaming into BigQuery, an atomic transaction in Firestore increments a global sequence counter (`ledger_seq`), retrieves the preceding record's digest, and stamps the cryptographic hash chain (`prev_hash` $\to$ `current_hash`).
  2. **Append-only storage:** BigQuery table governed by write-only IAM role for the service account (no `UPDATE/DELETE`).
  3. **WORM Anchoring:** Periodic hourly chain-head anchoring to a Google Cloud Storage bucket with **Object Retention Lock (Compliance mode)**.
  4. **Continuous verification:** Nightly audit job walks the hash chain and alerts on any sequence gap or cryptographic mismatch.
- `decision_outcomes_ledger` (30/60/90-day predicted vs. actual) drives recalibration of DAG edge weights and model thresholds using AIPW counterfactual estimation per §5.1.

### 6.3 Data and LLM security (per `data-security-llm-world.md`)
- **Layer 1 Token Vault & Identity Clusters:** PII is pseudonymized at ingestion before entering hot state or LLM context. Entity resolution generates a deterministic Identity Cluster Key (`tok_id_cluster_<hex16>`) that maps resolved aliases, accounts, and hardware IDs across partners, enabling agents to detect client recycling and fraud syndicates without exposing raw personal data. Markings/RBAC are enforced in the Ontology API (not in prompts).
- Prompt-injection defence: comms/ticket text is untrusted; tool outputs typed and sanitised; agents cannot call action tools directly — only emit intents.
- Secrets in Secret Manager; no secrets in repo; least-privilege service accounts per service; audit logs enabled.
- Threat model (STRIDE) and abuse cases are an engagement deliverable (`docs/engagement_plan.md` §7).

---

## 7. Experience requirements (technology-agnostic)
The frontend is re-derived from this section; existing scaffold and design docs are prototypes only.

| Persona view | Must show |
|---|---|
| Executive | Morning Briefing feed; causal-chain view with confidence/gate status; what-if slider; forecast + attribution (sums to 100%); chat with follow-ups; trade-off cards |
| AML investigator | Prioritised alert queue; one-screen dossier (evidence from all sources); graph view with plain-language explanation; SAR draft editor; approve/hold controls |
| Partner manager | Churn radar (value × risk); cohort map; playbook recommender; integrity cases; ring graph |
| Data platform | DQ board, contract breaches, freshness, ER conflicts, lineage |
| Compliance/Audit | Ledger explorer with chain-verify status; action history; access log |

Cross-cutting: every number has a provenance popover (metric, definition, version, as-of); "replay/cached" badge when serving fallback; accessibility (WCAG 2.2 AA target); streaming states for agent output.

---

## 8. Delivery structure — vertical slices with a cut line

Phases in `docs/engagement_plan.md`. Slices are demonstrable end-to-end (data → ontology → agent → UI → eval).

| Slice | Content | Depends on | Cut-line | Fallback if cut/late |
|---|---|---|---|---|
| **S0 Foundations** | Repo, IaC, CI/CD, contracts, generators (core), ontology core, metric registry, eval harness skeleton, observability skeleton, spikes S-01..S-06 | — | Must-have | — |
| **S1 Synthesis** | Causal DAG + cache, forecast + attribution, scenarios, Morning Briefing, chat follow-ups, recommendations, DQ board | S0 | Must-have | Cached briefing + replay |
| **S2 Module C** | Churn hazard, cohorts, playbooks (proposal only) | S1 | Must-have | Rules + z-score |
| **S3 Module B** | Opposite-trading, ring attribution, bonus/recycling/bot | S1 | **Cut-line above this** if time-boxed | Rules + graph |
| **S4 Module A** | Alert scorer, rings, SAR, withdrawal hold proposal | S3 graph | Stretch | Rules + templated SAR |
| **S5 Flywheel & hardening** | Outcome ledger, recalibration, chaos, soak, DR drill | S1+ | Must-have for "production" claim | — |

Rationale for order: S1 delivers the brief's highest bar (and needs the shared ontology); C is the cheapest module with a clear ML story; B and A share the graph engine.

---

## 9. Quality & evaluation (summary)
About two-thirds of engineering effort targets testing non-deterministic behaviour. Pillars (details in `docs/models_and_evals.md`):
1. **Golden sets** and labelled ground truth from seeded generators, split into *dev seeds*, *validation seeds*, and **sealed holdout seeds** (spec withheld from model authors).
2. **Baselines first:** each model must beat a documented rules/statistical baseline; report the delta, not just absolute metrics.
3. **Red-Line tests** (blocking): metric hallucination, citation coverage, causal-gate compliance, no-autonomous-write, PII leakage, prompt injection.
4. **Placebo-edge and circularity checks:** the system must reject planted false edges and detect unplanted holdout signals, otherwise "synthetic data validates itself."
5. **Agent evals:** trajectory tests (right tools, right order), multi-turn dialogues, refusal/escalation behaviour, cost/latency budgets.
6. **Non-functional:** load, chaos (kill instance, DLQ flood, LLM outage), cold-start, DR.

---

## 10. Production readiness (summary)
SLOs, environments (dev/stage/prod-like), IaC (Terraform), CI/CD with eval gates, observability (OpenTelemetry → Cloud Trace/Logging/Monitoring; LLM traces), corrected cost model (Cloud Run, Pub/Sub, BigQuery, GCS, Firestore, Secret Manager, KMS, Scheduler, Vertex AI, egress, plus Cube/Redis if chosen), runbooks, rollout (shadow → assist → act-with-approval), and handoff are specified in `docs/engagement_plan.md`. v2's "~$12.65/mo, <$20, $100 envelope" figures are withdrawn: they omitted several services and contradicted one another.

---

## 11. Risks and open questions
Top risks (full register with owners/mitigations in `docs/engagement_plan.md` §9):
1. **Synthetic circularity** — mitigated by hard negatives, sealed holdouts, placebo edges.
2. **Unverified stack claims** — mitigated by spikes before dependence.
3. **Scope vs. capacity** — mitigated by slices and cut-line.
4. **LLM variance/cost/outage** — provider-agnostic gateway, caching, cached fallback.
5. **Stateful in-memory components vs. serverless** — warm-start, min-instances, snapshot rehydrate.
6. **Portfolio credibility** — every figure labelled; evidence pack shipped.

Open questions: real-time definition per module (`[ASSUMPTION]` seconds for withdrawal check, minutes for briefing inputs); regulator template choice for SAR; graph scale ceiling; frontend stack (ADR-009).

---

## 12. Spec-kit hand-off

Suggested order of spec-kit invocations:
1. `/speckit-constitution` — encode §3.1 invariants, §0.2 labelling rule, testing bias, immutability, small-file rule, security rules.
2. One `/speckit-specify` per feature, in this order: `F00-foundations`, `F01-synthetic-foundry`, `F02-contracts-ingestion`, `F03-ontology-metrics`, `F04-eval-harness`, `F05-synthesis-engine`, `F06-conversational-analytics`, `F07-churn-radar`, `F08-partner-fraud`, `F09-client-aml`, `F10-governed-actions-ledger`, `F11-cockpit`, `F12-observability-sre`, `F13-flywheel`, `F14-hardening-dr`, `F15-portfolio-pack`.
3. `/speckit-clarify` on every spike-dependent feature after its spike ADR lands.
4. `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`, then implement with tests first.

Each feature spec must reference the relevant sections here, list acceptance from §5, and cite eval IDs from `docs/models_and_evals.md`.
