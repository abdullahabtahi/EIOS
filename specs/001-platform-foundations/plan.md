# Implementation Plan: Platform Foundations (F00)

**Branch**: `001-platform-foundations` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-platform-foundations/spec.md`

## Summary

F00 delivers the layer every later feature inherits: a Python monorepo skeleton, blocking CI/CD gates with hook registries for suites owned by F01–F04, three isolated Terraform-defined environments with per-service identity and managed secrets, a provider-neutral LLM gateway (stub provider only, no default model), a label/provenance checker, an ADR/spike record workflow with a feature-readiness check, and observability/cost scaffolding.

Technical approach:

- **Library + tools, not a product.** Shared behaviour lives in one importable package (`eios`), and every "check" (labels, ADR index, readiness, open-decision, cost, file size, forbidden literals) is a small standalone CLI under `tools/` that the pipeline and `make check` both run. This keeps one definition of each gate for local and CI use (FR-003, FR-004).
- **Gateway as an in-process library** behind a `Provider` protocol, with pluggable counter and replay stores (in-memory for dev/CI, Firestore in deployed environments). Model, price, rate-limit and cap values are configuration only and carry a verification tag (FR-021..FR-028).
- **Hook registries** (`evals/registry.yaml`) let F01–F04 register contract, eval-smoke and Red-Line suites without touching pipeline code. An empty registry reports "no suites registered"; any registered suite that fails fails the run (FR-006).
- **Infrastructure** is Terraform modules composed per environment, one cloud project per environment `[ASSUMPTION]`, with per-service identities, a managed secret store, an access-restricted eval-truth bucket and budget alerts (FR-013..FR-019, FR-038).
- **Decisions stay open.** No artefact names a default model, metric engine, frontend stack or API surface; a config-driven check enforces this (FR-028, FR-035, SC-011).

## Technical Context

**Language/Version**: Python (fixed by `initial_plan.md` §3). The exact minor version is the newest one supported by Cloud Run and every chosen tool on the day of implementation, recorded in `.python-version` and verified then `[SPIKE]`.

**Primary Dependencies**: FastAPI and Pydantic (pinned by `initial_plan.md` §3), OpenTelemetry SDK, Terraform. Tooling: uv (environments and lockfile), ruff (lint, format, banned-API import rules), mypy (strict type check), pytest with pytest-cov, a Python dependency auditor, a container/IaC scanner, a secret scanner, an SBOM generator, tflint. All tool choices are `[ASSUMPTION]`; none has a version pin here. Versions are fixed by the lockfile and CI configuration at implementation and verified then `[SPIKE]`. Rationale and alternatives in [research.md](./research.md).

**Storage**: Cloud Storage (evidence bucket with retention, eval-truth bucket, Terraform state), Firestore (gateway token counters and replay cache in deployed environments), Secret Manager. Local dev and CI use in-memory stores. No BigQuery in F00.

**Testing**: pytest with coverage gate at 80% `[TARGET]` on `src/eios`, `tools` and `services`; unit, contract and integration tiers under `tests/`; registry-driven eval-smoke and Red-Line hooks; a seeded faulty-change fixture set that proves each gate fails (SC-001).

**Target Platform**: GCP with Cloud Run services (`initial_plan.md` §3); GitHub Actions runners for CI `[ASSUMPTION]`; developer machines on macOS or Linux for local checks.

**Project Type**: Platform foundation: shared library, tooling CLIs, two skeleton services, infrastructure-as-code and CI definitions. No product surface.

**Performance Goals**: No latency or throughput target is set in F00. Pipeline duration and gateway overhead are measured first and targets are proposed from measurements in a later phase `[ASSUMPTION]`.

**Constraints**: No secrets in repo, images, logs or traces; no hard-coded model IDs, prices or providers; file size ceiling 800 lines with 200–400 typical; functions under 50 lines; immutable data (frozen models); validate at every boundary (constitution Engineering Constraints); no unverified version or price pins; ADR-002, 003, 009, 014 stay open.

**Scale/Scope**: Two skeleton services, one shared package, seven check tools, three environments, one bootstrap stack. Data volume is trivial fixture data only (spec Assumptions).

**Unknowns resolved in research**: all `NEEDS CLARIFICATION` items are resolved in [research.md](./research.md). One new dependency decision is surfaced there: the identity provider for approver claims (FR-018) needs its own ADR, opened before any feature uses it.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Principle / Constraint | Pre-research | Post-design |
|---|---|---|---|
| G1 | I. LLMs never compute business metrics. F00 has no metrics; the gateway returns text/structured output only and exposes no metric path. | PASS | PASS: gateway contract carries no numeric-claim field; `contracts/llm-gateway-interface.md` |
| G2 | II. No autonomous write-back. F00 adds no write path; identity-claims helper only reads verified claims; skeleton services expose no mutation endpoints. | PASS | PASS: skeleton services limited to health and correlation-echo; approver identity never in request models (FR-018) |
| G3 | III. Honest uncertainty. Gateway never returns invented output on outage (FR-025); label check forbids unlabelled numbers. | PASS | PASS: outcome enum has `unavailable` and `replay`, no `guess` |
| G4 | IV. Data as a product. F00 defines no data products; eval-truth location is separate and unreadable by services (FR-019). | PASS | PASS: eval-truth IAM grants only harness and pipeline identities |
| G5 | V. Provenance and labelling. Tag vocabulary, checker and cost model with pricing dates (FR-029..FR-031, FR-038). | PASS | PASS: `contracts/provenance-labels.md`, `contracts/cost-model.md`; this plan's own figures are tagged |
| G6 | VI. Eval-first, anti-circularity (non-negotiable). Sealed evaluation only by release-candidate CI; ground truth unreadable by agents (FR-008, FR-019). | PASS | PASS: separate release-candidate identity with attribute-restricted impersonation; `contracts/gate-hook-registry.md` |
| G7 | VII. Specialised agents, decoupled pipelines. F00 introduces no agents; gateway is a seam, not an agent. | PASS | PASS |
| G8 | VIII. Deterministic fallback and operability. Replay-or-unavailable fallback, correlation IDs, SLO/runbook stubs, rollback rehearsal (FR-010, FR-025, FR-036, FR-039). | PASS | PASS |
| G9 | Secrets and identity: Secret Manager, per-service identity, IdP claims. | PASS | PASS with follow-up: identity-provider ADR must be opened before use (research R-13) |
| G10 | Provider neutrality and token caps; model IDs and prices are config verified by S-01. | PASS | PASS: config schema requires a verification tag per value |
| G11 | Immutability, small files, small functions, boundary validation. | PASS | PASS: frozen-model test, file-size tool, ruff statement limits |
| G12 | Infrastructure as code with isolated environments; plan on every PR. | PASS | PASS: modules + per-env stacks, bootstrap exception documented |
| G13 | Open decisions stay open (ADR-002, 003, 009, 014); prototype `FEIOS/`, `DESIGN.MD`, `DESIGN_PLAN.md` is non-authoritative. | PASS | PASS: open-decision check, no default model, skeleton services expose no product API |
| G14 | Labelling regime applies to this plan: no unlabelled invented numbers, no real competitor brands, no unverified pins. | PASS | PASS: tool versions unpinned and marked `[SPIKE]` |

Result: no violations; the Complexity Tracking table is not needed. One documented exception to "nothing created by hand": the one-time bootstrap stack and its prerequisites (research R-05).

## Project Structure

### Documentation (this feature)

```text
specs/001-platform-foundations/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── llm-gateway-interface.md
│   ├── llm-gateway-config.schema.json
│   ├── llm-call-trace.schema.json
│   ├── pipeline-run-record.schema.json
│   ├── feature-dependencies.schema.json
│   ├── provenance-labels.md
│   ├── decision-and-spike-records.md
│   ├── gate-hook-registry.md
│   └── cost-model.md
├── checklists/requirements.md
└── tasks.md             # created later by /speckit-tasks
```

### Source Code (repository root)

```text
.github/workflows/
├── pr.yml                       # all blocking gates on every change
├── promote-stage.yml            # on merge to main
├── promote-prod-like.yml        # manual, protected environment approval
└── release-candidate.yml        # only workflow allowed to run sealed evals

infra/
├── bootstrap/                   # one-time: state bucket, CI identity federation
├── modules/
│   ├── project_baseline/        # APIs, logging, org-policy-style guardrails
│   ├── service_identity/        # one service account + declared role list
│   ├── secret_store/            # managed store + KMS key ring (T079)
│   ├── eval_truth_store/        # restricted bucket for ground truth
│   ├── evidence_store/          # pipeline run records, retention
│   ├── artifact_registry/
│   ├── run_service/             # Cloud Run service wiring, min-instances policy
│   ├── state_stores/            # Firestore for gateway counters and replay
│   └── budget_alerts/           # 50/80/100% thresholds [TARGET]
├── envs/
│   ├── dev/
│   ├── stage/
│   └── prod-like/
└── identities.yaml              # extra file (T086)

src/eios/
├── common/                      # correlation, logging redaction, errors, validation
│   ├── correlation.py
│   ├── logging_redaction.py
│   ├── untrusted_text.py
│   ├── identity_claims.py
│   ├── secret_reader.py         # extra file (T075)
│   └── otel.py
└── llm_gateway/
    ├── gateway.py               # single access point
    ├── models.py                # frozen request/response/outcome/trace models
    ├── config.py                # config loading + verification tags
    ├── caps.py                  # daily token cap + thresholds
    ├── replay_cache.py
    ├── trace.py
    ├── stores/{memory.py,firestore.py}
    └── providers/{base.py,stub.py}

services/
├── skeleton_edge/               # health + forwards a correlated call to core
│   ├── app.py  Dockerfile  slo.md  runbook.md  warm_start.md
└── skeleton_core/
    ├── app.py  Dockerfile  slo.md  runbook.md  warm_start.md

tools/
├── label_check/
├── adr_check/
├── readiness/
├── open_decision_check/
├── cost_check/
├── gates/                       # hook runner, run-record writer
├── repo_checks/                 # file size, forbidden literals, frozen models
├── records/                     # extra package (T020)
├── common/                      # extra package (T018)
├── infra_checks/                # extra package (T069)
├── prompt_lock/                 # extra package (US3)
└── budget_probe/                # extra package (US6)

evals/
├── golden/  suites/  fixtures/  reports/     # layout from docs/models_and_evals.md §7
├── registry.yaml                # hook registry (empty in F00)
└── cli.py

prompts/
├── <prompt-id>/v<N>.md
└── prompts.lock.json

config/
├── llm_gateway.dev.yaml  llm_gateway.stage.yaml  llm_gateway.prod-like.yaml
├── labels.yaml
├── open_decisions.yaml
├── forbidden_literals.yaml
├── repo_checks.yaml             # extra file (T048)
├── gates.yaml                   # extra file (T042)
├── quarantine.yaml              # extra file (T047)
├── rollback.yaml                # extra file (T089)
├── cost_linkage.yaml            # extra file (US6)
├── budgets.yaml                 # extra file (US6)
├── risk_exceptions.yaml         # extra file
└── label_allowlist.yaml         # extra file (US4)

docs/
├── adr/                         # NNN-title.md, spike records beside ADRs
├── cost_model.csv
├── conventions.md
├── feature_register.yaml        # extra file (T174)
├── evidence/                    # extra tree (T056)
└── runbooks/

tests/
├── unit/  contract/  integration/
├── fixtures/faulty_changes/     # one deliberately failing change per gate
└── support/                     # extra tree (T009)

schemas/                         # extra tree (T021)

specs/<feature>/dependencies.yaml # extra layout file

Makefile  pyproject.toml  uv.lock  .python-version  docker-compose.dev.yml
```

**Structure Decision**: A single-root Python monorepo with one library package (`eios`), a separate `tools/` tree for gate CLIs, `services/` for deployable skeletons and `infra/` for Terraform. Every path above traces to a requirement: `infra/` to FR-013..FR-019; `src/eios/llm_gateway` to FR-021..FR-028; `tools/label_check` to FR-029..FR-031; `tools/adr_check`, `tools/readiness` and `tools/open_decision_check` to FR-032..FR-035; `evals/registry.yaml` to FR-006 and FR-008; `docs/cost_model.csv` to FR-038; `services/*` to FR-036 and FR-039; `prompts/` to FR-037. The layout deliberately leaves room for F01–F04 (contracts, generators, ontology, metric registry) without reserving names for decisions that are still open.

## Complexity Tracking

No constitution violations; nothing to justify.
