<!--
Sync Impact Report (temporary; remove before commit)
- Version change: (unfilled template) → 1.0.0
- Modified principles: none (initial ratification)
- Added principles: I–VIII (derived from initial_plan.md §3.1 invariants, §0.2 labelling regime,
  docs/models_and_evals.md, docs/engagement_plan.md)
- Added sections: Engineering Constraints, Delivery Workflow and Quality Gates, Governance
- Removed sections: none
- Deferred TODOs: none. Stack choices (LLM, metric engine, frontend, API surface) are intentionally
  NOT fixed here; they are open ADRs (ADR-002, 003, 009, 014) and resolved via spikes.
-->
# EIOS Constitution

Governs the Enterprise Intelligence Operating System, a simulated forward-deployed engineering
engagement (POC → Production) used as a portfolio piece. `initial_plan.md` (v3) is the master spec;
`docs/brief/*` are the canonical requirement sources and win on conflict. This constitution wins over
every other document except the requirements in the briefs.

## Core Principles

### I. LLMs Never Compute Business Metrics
Every quantitative value shown to a user or used in a decision MUST come from a deterministic tool
call through the metric registry or a registered Ontology function (for example `get_metric`).
An LLM MAY phrase, summarise and route; it MUST NOT calculate, estimate or recall numbers.
The Auditor Gate MUST block any output containing a number not traceable to a tool result.
Rationale: hallucinated figures are the fastest way to destroy trust in an enterprise system.

### II. No Autonomous Write-Back (NON-NEGOTIABLE)
Agents have read and propose tools only; no agent-callable execute tool may exist. Every mutation is
an Action Intent that is signed with Cloud KMS (ECDSA P-256), single-use, nonce-bound and expiring,
approved by an authenticated human (four-eyes for high severity), and executed only by the simulated
write-back sink. Every decision is recorded in the tamper-evident decision ledger.
There is no "autonomous" rollout mode.
Rationale: consequences of fraud and compliance actions are irreversible and regulated.

### III. Honest Uncertainty and the Causal-Evidence Gate
A causal assertion MUST pass the gate: effect confidence interval excludes zero, placebo-treatment
refuter effect ≈ 0, random-common-cause and data-subset refuters stable, confidence ≥ 0.80.
Otherwise the system MUST say "correlation detected; insufficient evidence for causation."
Unanswerable questions MUST be answered with "insufficient data", never with invention.
Rationale: over-asserted causality is the most likely failure of a synthesis engine.

### IV. Data as a Product, Ontology-Only Access
Every domain dataset is a versioned data product with a contract (schema, freshness SLA, quality
rules, markings, semantic metrics). Agents and the cockpit MUST consume products only through the
Ontology API / OMCP, never raw tables. Contract violations MUST go to a DLQ, raise an alert and mark
the product `DEGRADED`; they MUST NOT be silently dropped. Security markings (PII, sensitive
compliance, partner commercial) are enforced server-side and PII is pseudonymised before any LLM.
Rationale: governed access is what makes an ontology an operating system rather than a dashboard.

### V. Provenance and Labelling
Every figure or claim MUST carry one of `[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`,
`[SPIKE]`. Any number shown in the cockpit, an eval report or the case study MUST trace to a brief
citation, a generator run (seed + git SHA + dataset hash) or an eval report. Unlabelled invented
numbers, real brand names as competitors, and unverified library, model or price pins are forbidden.
Claims tagged `[SPIKE]` remain unverified until the spike closes with an ADR.
Rationale: the portfolio's credibility rests on evidence, not theatre.

### VI. Eval-First, Baselines and Anti-Circularity (NON-NEGOTIABLE)
Every model and agent capability MUST have a naive baseline implemented first and MUST beat it by a
pre-registered margin, reported as deltas with uncertainty on sealed-seed holdouts. Data is split
into dev, validation and sealed seeds; sealed results are produced only by CI on release candidates.
Synthetic data MUST include hard negatives, label noise, placebo causal edges and typologies unseen by
model authors; ground-truth labels live in an eval-only bucket unreadable by agents, models at
inference and the UI. Red-Line tests RL-1..RL-7 are blocking in CI. Tests are written before
implementation (red → green → refactor) with a minimum of 80% coverage on unit-testable code.
Rationale: about two-thirds of effort belongs to testing non-deterministic behaviour.

### VII. Specialised Agents and Decoupled Pipelines
There is no God Agent: specialised sub-agents sit behind one Supervisory Router. Batch and streaming
pipelines MUST remain decoupled. Structural causal models are computed and refuted offline (nightly,
cached); only parametric propagation runs in an interactive turn.
Rationale: bounded agents are testable; coupled pipelines and live model fitting are not.

### VIII. Deterministic Fallback and Operability
LLM or provider outage MUST degrade to cached output labelled with a replay badge, never to invented
output. Every service has SLOs, OpenTelemetry traces with correlation IDs, runbooks and a rollback
path. Stateful in-memory components MUST have a documented warm-start strategy.
Rationale: production readiness is demonstrated by behaviour under failure.

## Engineering Constraints

- **Secrets and identity:** no secrets in the repository; Secret Manager plus CI secret scanning;
  one service account per service; approver identity comes from IdP claims, never the request body.
- **Provider neutrality:** LLM access goes through a provider-agnostic gateway with per-day token
  caps; model IDs and prices are configuration verified by spike S-01, never hard-coded.
- **Immutability and structure:** prefer immutable data structures; files are focused (target
  200–400 lines, hard maximum 800); functions are small (< 50 lines); errors are handled explicitly
  and never swallowed.
- **Validation at boundaries:** all external input, API responses and file content are validated
  against schema before use; free text from tickets and comms is untrusted data.
- **Infrastructure as code:** all cloud resources are declared in Terraform; environments are
  `dev`, `stage`, `prod-like`, each isolated.
- **Open decisions stay open:** the frontend stack (ADR-009), API surface (ADR-014), metric engine
  (ADR-003) and LLM selection (ADR-002) MUST NOT be assumed in specs; the `FEIOS/`, `DESIGN.MD` and
  `DESIGN_PLAN.md` website prototype is non-authoritative and MUST NOT drive UI requirements.

## Delivery Workflow and Quality Gates

- **Spec-driven order:** constitution → specify → clarify → plan → tasks → analyze → implement.
  Features follow the F00–F15 decomposition in `initial_plan.md` §12 and the slice plan S0–S5 with
  its cut line; scope above the cut line is dropped before quality is.
- **Spikes before dependence:** a feature depending on a `[SPIKE]` claim MUST NOT start until that
  spike closes with an ADR in `FEIOS/docs/adr/` (template in `FEIOS/docs/spikes_and_adrs.md`).
- **CI gates (blocking):** lint and type check, unit tests with ≥ 80% coverage, contract tests,
  eval smoke on dev seeds, Red-Line suite, container vulnerability scan, `terraform validate/plan`.
  Merge to stage adds validation-seed evals; release candidates add sealed-seed evals.
- **Review:** code is reviewed after writing; CRITICAL and HIGH findings MUST be fixed before merge;
  security review precedes any commit touching auth, signing, ledger or PII paths.
- **Phase gates:** each phase (P0–P4) ends with a consistency check of spec ↔ plan ↔ tasks ↔ code ↔
  eval reports and a one-page report against the exit criteria in `docs/engagement_plan.md`.
- **Commits:** conventional types (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`);
  commits and pushes happen only on explicit request.

## Governance

This constitution supersedes all other practices and documents except the requirements in
`docs/brief/*`. Amendments MUST be made through `/speckit-constitution`, state their rationale, list
affected principles and dependent artefacts, and include a migration note for any in-flight feature.
Versioning is semantic: MAJOR for removing or redefining a principle in a backward-incompatible way;
MINOR for adding a principle or materially expanding guidance; PATCH for clarifications.
Principles II and VI are NON-NEGOTIABLE and may be amended only by a MAJOR version with an explicit
recorded justification. Every plan and `/speckit-analyze` run MUST include a constitution-compliance
check; any violation MUST be fixed or recorded with justification in the plan's complexity tracking.
Runtime guidance for AI assistants lives in `CLAUDE.md`.

**Version**: 1.0.0 | **Ratified**: 2026-09-29 | **Last Amended**: 2026-09-29
