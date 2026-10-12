# Research: Platform Foundations (F00)

**Feature**: `001-platform-foundations` | **Date**: 2026-09-30 | **Plan**: [plan.md](./plan.md)

Every tool choice below is `[ASSUMPTION]`. No version is pinned; versions are fixed by the lockfile and CI config at implementation and verified then `[SPIKE]`. GitHub prior-art searches for a ready-made platform-foundation skeleton covering this combination (gateway + label check + ADR readiness) returned nothing adoptable, so each piece is assembled from standard tools.

## R-01: CI/CD system

- **Decision**: GitHub Actions with Workload Identity Federation (no long-lived cloud keys). Four workflows: `pr.yml` (all blocking gates), `promote-stage.yml` (on merge), `promote-prod-like.yml` (manual, protected-environment approval), `release-candidate.yml` (the only path allowed to run sealed evals).
- **Rationale**: The delivery pipeline in `docs/engagement_plan.md` §4 needs per-PR gates, staged promotion, manual approval and an isolated sealed-eval path. Protected environments and per-workflow federation claims map directly onto those needs (FR-004..FR-012). Federation removes stored credentials (constitution secrets constraint).
- **Alternatives**: Cloud Build (native to GCP, but weaker approval and PR-status ergonomics for a portfolio repo that reviewers browse on GitHub); GitLab CI (repo is not there). Both remain viable; the gate logic lives in `make` targets and `tools/`, so the CI system is swappable.

## R-02: Python toolchain

- **Decision**: uv for environments and lockfile; ruff for lint, format and banned-import rules; mypy in strict mode; pytest with pytest-cov and `--cov-fail-under=80` `[TARGET]`. A `Makefile` exposes `make setup` and `make check`; CI calls the same targets.
- **Rationale**: One lockfile gives reproducible builds; `make check` gives engineers the exact CI gate set locally (FR-003, SC-003).
- **Alternatives**: Poetry or pip-tools (slower, no advantage here); pyright (comparable; mypy chosen for plugin ecosystem with Pydantic).

## R-03: Vulnerability, secret and SBOM scanning

- **Decision**: a Python dependency auditor, a container and IaC scanner, a secret scanner (run on the working tree and on history when a git repo exists), and an SBOM generator whose output is stored as a pipeline artefact. All block on findings at or above a configured severity `[TARGET]`; accepted exceptions live in a reviewed allowlist with owner and expiry.
- **Rationale**: FR-009 and FR-010 require blocking scans and an SBOM per release candidate. An expiring allowlist prevents silent permanent waivers.
- **Alternatives**: single all-in-one scanner (fewer tools, but less coverage per domain); manual review (not a gate).

## R-04: Gate proof via faulty-change fixtures

- **Decision**: `tests/fixtures/faulty_changes/` holds one minimal deliberately broken change per gate (lint error, type error, coverage drop, unlabelled number, hard-coded model ID, oversized file, secret-shaped string, etc.). A meta-test applies each fixture in a temp copy and asserts the matching gate fails.
- **Rationale**: SC-001 requires demonstrating that each gate actually blocks. Without this a gate that always passes looks identical to a working one.
- **Alternatives**: rely on reviewers noticing (not a gate).

## R-05: Bootstrap exception

- **Decision**: `infra/bootstrap/` is applied once by a human with elevated rights. It creates the remote-state bucket, CI federation and the per-environment projects' baseline. It is the single documented exception to "nothing created by hand". External prerequisites: a billing account and a parent folder or organisation. Runbook in `docs/runbooks/`.
- **Rationale**: State storage and CI identity cannot be created by the pipeline that depends on them. Documenting the exception keeps FR-013 honest.
- **Alternatives**: manual console setup (undocumented, unreproducible); a third-party bootstrap tool (extra dependency for a one-time step).

## R-06: Environment isolation

- **Decision**: one cloud project per environment (dev, stage, prod-like) `[ASSUMPTION]`, composed from shared Terraform modules with per-environment stacks. No shared credentials, buckets or state prefixes across environments. Promotion moves artefacts (images by digest), not data.
- **Rationale**: Project boundaries give hard IAM and quota isolation, which FR-013..FR-016 require, at low cost for a small team.
- **Alternatives**: one project with prefixes (weak isolation); separate organisations (excessive for the scope).

## R-07: Service identity and least privilege

- **Decision**: a `service_identity` module produces one service account per service with an explicit declared role list. A check fails on any wildcard or project-wide editor grant. Eval-truth access goes only to the harness and pipeline identities; a separate release-candidate identity is impersonable only by the release-candidate workflow (attribute-restricted).
- **Rationale**: FR-014, FR-017 and FR-019 plus constitution VI (anti-circularity): agents and services must be unable to read ground truth.
- **Alternatives**: shared runtime account (violates the constitution).

## R-08: Secrets

- **Decision**: Secret Manager; Terraform creates secret containers only, never values. Services read at runtime through their own identity. A repo secret scanner and log-redaction helper (`logging_redaction.py`) cover leakage. No `.env` files are committed.
- **Rationale**: FR-015, FR-016 and the constitution's "no secrets in repo" constraint.
- **Alternatives**: values in Terraform state (leaks into state); environment files (leak into images).

## R-09: LLM gateway design

- **Decision**: an in-process Python library with one access point, a `Provider` protocol, and a stub provider only. Config (per environment) carries the provider label, model identifier, prices, rate limits, per-day token cap and a verification tag per value; the config loader rejects any value lacking a tag and refuses to start with no model configured (no default model). Outcomes are `ok`, `replay`, `unavailable`, `cap_reached`, never a guess. Thresholds at 50/80/100% of the daily cap `[TARGET]` emit warnings and then block.
- **Rationale**: FR-021..FR-028 and ADR-002/S-01 stay open. An in-process seam is the smallest design that enforces caps and traces for every caller without adding a network service before S-01 is decided.
- **Alternatives**: standalone gateway service (extra ops cost, latency and a new failure domain before the need is shown); vendor SDK calls scattered through services (violates FR-021 and provider neutrality).

## R-10: Gateway stores

- **Decision**: counter and replay stores sit behind small interfaces; `memory` for dev/CI, `firestore` for deployed environments. Replay keys hash the full request (prompt id and version, inputs, config identity). The replay entry records the original timestamp so the "replay badge" can show age.
- **Rationale**: FR-024/FR-025 need deterministic fallback; shared state is required once more than one instance runs. Firestore is already in the stack for approvals (ADR-010).
- **Alternatives**: Redis (new component); local disk (not shared across instances).

## R-11: Traces and correlation

- **Decision**: OpenTelemetry spans plus structured JSON logs. A correlation ID is generated at the edge, carried by header and context, and stamped on every log line, span, gateway trace and pipeline record. `skeleton_edge` calls `skeleton_core` to prove propagation end to end. Traces record prompt id/version, config identity, token counts, cost, latency and outcome, never raw secrets; untrusted text is wrapped by `untrusted_text.py` so prompt-injection tests can hook in later (RL-6).
- **Rationale**: FR-036, FR-037, FR-039.
- **Alternatives**: vendor-specific tracing SDK (lock-in).

## R-12: Label and provenance check

- **Decision**: `tools/label_check` scans Markdown and config for numeric claims and requires an adjacent tag from `config/labels.yaml` (`[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]`). It also flags real competitor brand names and version/price/model pins that lack a tag or verification note, using `config/forbidden_literals.yaml`. Allowlist per file with reason.
- **Rationale**: FR-029..FR-031 and constitution V. A heuristic is acceptable because the check errs toward flagging and offers a reviewed allowlist.
- **Alternatives**: manual review only (not blocking); full NLP claim detection (over-engineered).

## R-13: Identity provider for approver claims

- **Decision**: F00 provides `identity_claims.py` that reads verified claims from a token the platform edge has already validated, and ships no provider. The choice of identity provider is undecided in any doc; a new ADR is opened as `Proposed` before any feature uses approver identity (F13/F14 territory). Until then approver identity is never read from request bodies (FR-018).
- **Rationale**: Deferring keeps ADR scope honest and avoids an implicit decision.
- **Alternatives**: choose one now (unjustified without a spike).

## R-14: ADR, spike and readiness workflow

- **Decision**: `docs/adr/NNN-title.md` follows the template in `docs/spikes_and_adrs.md`. `tools/adr_check` validates required fields, allowed statuses and that the index in `docs/spikes_and_adrs.md` agrees with the files: `Accepted` requires a file; `Proposed` and `Open` may lack one. Features declare dependencies in a small machine-readable block (`feature-dependencies.schema.json`); `tools/readiness` fails when a feature depends on a `[SPIKE]` whose spike is not closed with an ADR. `tools/open_decision_check` fails if ADR-002/003/009/014 names appear as chosen values in code or config (`config/open_decisions.yaml`).
- **Rationale**: FR-032..FR-035, SC-011, and the rule that a feature depending on a `[SPIKE]` must not start until the spike closes.
- **Alternatives**: free-form ADRs (unenforceable).

## R-15: Hook registry for later suites

- **Decision**: `evals/registry.yaml` lists suites by id, tier (`contract`, `eval_smoke`, `red_line`, `validation`, `sealed`), command and owner feature. The runner prints "no suites registered" when empty, fails on any failing or missing registered suite, and refuses to run `sealed` suites unless invoked by the release-candidate workflow identity. Reports go to `evals/reports/` and are referenced from the pipeline run record.
- **Rationale**: FR-006, FR-008 and constitution VI. F01–F04 add suites without editing pipeline code.
- **Alternatives**: hard-code future suites in workflows (couples F00 to later features).

## R-16: Pipeline run record and evidence

- **Decision**: each pipeline run writes a JSON record (`pipeline-run-record.schema.json`) with commit, gates run and outcomes, artefact digests, SBOM reference and approver identity where relevant, stored in the evidence bucket with a retention policy `[ASSUMPTION]`.
- **Rationale**: FR-010, FR-011, and the portfolio need for auditable evidence.
- **Alternatives**: rely on CI logs (expire, not structured).

## R-17: Cost model and budget alerts

- **Decision**: `docs/cost_model.csv` has one row per cost driver with unit, assumed quantity, unit price, price source, pricing-verified date and tag. `tools/cost_check` fails on rows lacking a tag, source or date, or with pricing older than a configured age `[TARGET]`. Terraform `budget_alerts` sets 50/80/100% thresholds per environment `[TARGET]`. Values are `[ASSUMPTION]` until measured.
- **Rationale**: FR-038, FR-039 and the record that earlier plan versions had contradictory cost figures.
- **Alternatives**: spreadsheet outside the repo (not checked).

## R-18: Skeleton services, SLOs, warm start and rollback

- **Decision**: two Cloud Run skeleton services (`skeleton_edge`, `skeleton_core`) expose health and a correlation echo only. Each carries `slo.md`, `runbook.md` and `warm_start.md` stubs with SLO figures left `[TARGET]` and unset until measured. Rollback is redeploying the previous revision by traffic shift plus a configuration flag; a rehearsal step in `promote-prod-like.yml` documentation records the elapsed time against the `[TARGET]` bound in the spec.
- **Rationale**: FR-036, FR-039 and constitution VIII. Skeletons prove wiring without adding a product API (ADR-014 open).
- **Alternatives**: no services (cannot prove propagation, promotion or rollback).

## R-19: Prompt versioning without git

- **Decision**: prompts live at `prompts/<id>/v<N>.md` with `prompts.lock.json` mapping each version to a content hash. A check fails if a released version's content changes or a prompt is referenced without a lock entry. Works with or without a git repository.
- **Rationale**: FR-037; the project is not yet a git repo, so a hash lockfile is the portable option.
- **Alternatives**: rely on git history (unavailable now).

## R-20: Repository conventions and size limits

- **Decision**: `docs/conventions.md` records naming, layout, immutability rules (frozen Pydantic models and dataclasses, checked by a repo check) and the size limits: 200–400 lines typical, 800 hard maximum, functions under 50 lines. `tools/repo_checks` enforces the file-size ceiling and forbidden literals; ruff enforces function-length and complexity limits.
- **Rationale**: FR-001..FR-003 and the constitution's Engineering Constraints.
- **Alternatives**: reviewer discipline only.

## Resolved unknowns

| Unknown | Resolution |
|---|---|
| CI system | R-01 |
| Toolchain | R-02 |
| Scanners and SBOM | R-03 |
| Bootstrapping | R-05 |
| Environment isolation | R-06 |
| Identity provider | R-13 (new ADR needed before use) |
| Performance goals | Not set in F00; measure first (plan Technical Context) |

No `NEEDS CLARIFICATION` remains.
