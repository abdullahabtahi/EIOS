# Red-Team Findings — v2 → v3

Companion to `initial_plan.md` v3. History of v1 → v2 stays in `docs/red_team_findings.md`. This document records why v3 differs from v2. Lens: Tier-1 AI Practice Partner × Forward Deployed Systems Architect × Cloud Solution Architect, plus a pre-mortem ("it is six months from now and the engagement failed — why?").

## Reframe

The project is no longer a hackathon entry (that event has ended). It is a **simulated forward-deployed engineering engagement, POC → production**, used as a portfolio piece. Consequences: success is judged by rigour and honesty of evidence, operability, and handoff, not by demo theatre.

## Findings and fixes

| # | Severity | Finding (v2) | Fix (v3) | Where |
|---|---|---|---|---|
| 1 | Critical | Hackathon framing: no phases, SLOs, environments, runbooks, handoff | FDE engagement structure with exit criteria per phase | `engagement_plan.md` §1–12 |
| 2 | Critical | Invented numbers presented as facts (unsourced scale, "5x recruiting cost", "80% of volumes", Amy's stats, case-study percentages, CR84920, AP-1029, Boom 1000, named poaching competitors, "<450ms", jurisdiction names) | Labelling regime (`[BRIEF]`/`[ASSUMPTION]`/`[ILLUSTRATIVE]`/`[TARGET]`/`[SPIKE]`); everything invented demoted or removed; provenance rule | `initial_plan.md` §0.2; `synthetic_data_strategy.md` |
| 3 | Critical | Synthetic circularity: models detect what the generator planted | Hard negatives, sealed holdout typologies, seed splits, label noise, placebo edges, eval-only ground truth | `synthetic_data_strategy.md`; `models_and_evals.md` §1 |
| 4 | Critical | Causal gate logic backwards ("refutation p > 0.05 → assert"?), and live DoWhy refutation implied | Correct gate: CI excludes 0, **placebo refuter ≈ 0**, random-common-cause and subset stable, confidence ≥ 0.80; refutation precomputed nightly and cached | `initial_plan.md` §3/§5.1; `models_and_evals.md` §5; ADR-005 |
| 5 | High | "Gemini 3.8 Flash" and other stack pins unverified | Provider-agnostic gateway; model IDs/pricing/caching verified in S-01 | `spikes_and_adrs.md` |
| 6 | High | Cube Core assumed; poor fit for scale-to-zero; adds Node + Redis | Metric-registry contract is the invariant; engine decided in S-02 | S-02, ADR-003 |
| 7 | High | HMAC-SHA256 Action Intent tokens: symmetric, no rotation, no replay control | Cloud KMS ECDSA P-256, nonce, ~15 min expiry, Firestore idempotency, `kid` rotation | `initial_plan.md` §6; ADR-006 |
| 8 | High | "Immutable BigQuery ledger": BigQuery is not immutable | Write-only IAM + hash chain + retention-locked GCS anchors + daily verifier + tamper drill | ADR-007 |
| 9 | High | Cloud Workflows as approval state machine | Approval service (Cloud Run + Firestore) holds state; Workflows only for scheduled jobs | ADR-010 |
| 10 | High | No executor for approved actions | Simulated write-back sink (mock core-systems API, chaos-failable) | ADR-011 |
| 11 | High | In-memory DuckDB/NetworkX on scale-to-zero Cloud Run loses state | Parquet warm-start; min-instances=1 in prod-like; documented ceiling; production alternative named | ADR-004, ADR-012 |
| 12 | High | Shared-IP false merges in graph rings | Hub suppression; hub false-merge rate is an eval metric | `models_and_evals.md` §2 |
| 13 | High | Cost figures (~$12.65 / < $20 / $100) omitted services and conflicted | Withdrawn; component-level cost model reconciled to real bill | `engagement_plan.md` §6 |
| 14 | Medium | No baselines: "AI wins" claims unfalsifiable | Baseline per model; report deltas on sealed seeds | `models_and_evals.md` |
| 15 | Medium | Module A treated as unsourced | `docs/brief/monitoring.md` is its source; anchors cited | `initial_plan.md` §2, §5.4 |
| 16 | Medium | Requirement traceability missing | Brief → capability → slice → eval table | `initial_plan.md` §2 |
| 17 | Medium | Entity resolution and DQ under-specified | ER in L1, DQ board, spike S-07 | ADR-008 |
| 18 | Medium | Scope too large for one team | Slices S0–S5, cut-line above S3, per-slice fallbacks | `initial_plan.md` §8 |
| 19 | Medium | UI decisions leaked from the website prototype | `FEIOS/`, `DESIGN.MD`, `DESIGN_PLAN.md` declared non-authoritative; frontend stack is open ADR-009; UI derived from persona requirements | `initial_plan.md` §7; ADR-009 |
| 20 | Low | Monolithic 74 KB spec | Master spec + companion docs, each ≤ ~800 lines | `initial_plan.md` header |

## Pre-mortem — most likely failure modes and their pre-emptions

| Failure story | Pre-emption |
|---|---|
| "The demo looked great but a reviewer asked where 84% came from and there was no answer." | Provenance rule; evidence pack; `[ILLUSTRATIVE]` labels |
| "Models scored 0.99 AUC because they learned the generator." | Anti-circularity controls; sealed seeds evaluated only in CI |
| "The agent stated a causal claim that was really a correlation." | Corrected causal gate; RL-3 blocking |
| "An agent action reached a system without approval." | No execute tool for agents; RL-4; signed single-use intents |
| "It only worked on my laptop / cold start broke the graph." | Warm-start, prod-like environment, one-command demo |
| "Ran out of time; nothing finished." | Slices with cut-line; S0–S2 alone tell the full story |
| "Costs surprised me." | Component cost model; budget alerts; token caps |

## Open items carried into spec-kit

Spikes S-01..S-07 and ADR-009 / ADR-014 (frontend and API surface) are intentionally undecided; each blocks only the features that depend on it (see `spikes_and_adrs.md`).
