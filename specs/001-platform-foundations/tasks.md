# Tasks: Platform Foundations (F00)

**Input**: Design documents from `/specs/001-platform-foundations/`
**Path convention**: every code, config, docs, infra and test path in this file is relative to `FEIOS/` (the production repository root). Planning documents (`specs/`, `initial_plan.md`, `docs/brief/`) stay at the workspace root.
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md, contracts/ (all present)
**Tests**: MANDATORY. Constitution requires test-first (RED, then GREEN, then refactor). Every implementation task is preceded by a test task that must fail first. Coverage gate is 80% `[TARGET]`.
**Organisation**: by user story (US1..US6), so each story can be built, tested and demonstrated on its own.

## Format

`- [ ] T### [P?] [US#?] Description with file path`

- `[P]`: touches different files from every other incomplete task in its group and has no unmet dependency. Safe to run in parallel.
- `[US#]`: story label. Present only in story phases (Phases 3 to 8). Absent in Setup, Foundational and Polish.
- "RED" in a task means: write the test, run it, and confirm it fails for the right reason before starting the matching implementation task.

## Ground rules that apply to every task

- All numbers in this file are tagged. Ceilings, thresholds and time bounds are `[TARGET]` (commitments to measure, not claims). Tool choices are `[ASSUMPTION]`. Tool and library versions, vulnerable-dependency choices and prices are `[SPIKE]` (unverified until fixed at implementation and recorded).
- No task may name a default model, metric engine, frontend stack or API surface (ADR-002, 003, 009, 014 stay open; SC-011).
- No secret, secret-shaped literal or real competitor brand is committed. Test data of that shape is generated at test time by `tests/support/secret_shapes.py`.
- All runtime models are frozen (immutable). Updates return new instances.
- Files stay under 800 lines `[TARGET]`, functions under 50 lines `[TARGET]`, per `docs/conventions.md`.
- Tools run as `uv run python -m tools.<name>`. Tests import with `pythonpath = ["src", "."]` and `--import-mode=importlib`.
- Do not create a git repository or commit unless the user asks. Where a revision id is needed and no git exists, use a content hash.

## Path conventions

Single-root Python monorepo per plan.md: `src/eios/`, `tools/`, `services/`, `infra/`, `evals/`, `prompts/`, `config/`, `docs/`, `tests/`, `schemas/`, `.github/workflows/`.

---

## Phase 1: Setup (shared project initialisation)

**Purpose**: an empty but runnable, lintable, testable skeleton. Nothing here is story-specific.

- [X] T001 Create `pyproject.toml` at the repo root: `[tool.uv] package = false`; pytest `pythonpath = ["src", "."]`, `addopts` including `--import-mode=importlib --strict-markers`; coverage `fail_under = 80` `[TARGET]` over `src/eios`, `tools`, `services`; mypy `strict = true`; ruff lint and format config with function-length and statement limits at 50 lines `[TARGET]` and a `banned-api` table left empty (filled in T128). No dependency versions typed by hand; `uv add` writes them.
- [X] T002 Create `.python-version` containing the newest Python minor supported by Cloud Run and every chosen tool on the day of implementation. Record the check that established it in `docs/conventions.md` (T005) tagged `[SPIKE]`.
- [X] T003 Create the directory skeleton with placeholder files so paths exist: `src/eios/common/__init__.py`, `src/eios/llm_gateway/__init__.py`, `tools/__init__.py`, `services/.gitkeep`, `evals/{golden,suites,fixtures,reports}/.gitkeep`, `prompts/.gitkeep`, `config/.gitkeep`, `docs/adr/.gitkeep`, `docs/runbooks/.gitkeep`, `docs/evidence/.gitkeep`, `infra/{bootstrap,modules,envs}/.gitkeep`, `schemas/.gitkeep`, `tests/{unit,contract,integration,support}/__init__.py`, `tests/fixtures/.gitkeep`.
- [X] T004 [P] Create `.gitignore` covering virtual environments, caches, Terraform state and `.terraform/`, `evals/reports/*` (keep `.gitkeep`), local env files, coverage output.
- [X] T005 [P] Create `docs/conventions.md` (FR-001, FR-002): where code, contracts, evals, infrastructure, prompts, documents and decision records live; file ceiling 800 lines `[TARGET]` with 200 to 400 typical; functions under 50 lines `[TARGET]`; immutable-by-default data; explicit error handling; validation at every external boundary; free text from external sources is untrusted data (FR-020); the tag vocabulary and how to attach provenance; an empty "Tooling register" table (columns: role, tool, chosen on, verified version, tag) and a section listing planned deviations from plan.md (filled in T221).
- [X] T006 Create `Makefile` with targets `setup` (`uv sync`), `check` (delegates to `uv run python -m tools.gates.local`, wired in T052), `test`, `lint`, `types`. One entry point, same gates as CI (FR-003). Depends on T001.
- [X] T007 Run `uv lock` and add development dependencies chosen by role: test runner with coverage, linter and formatter, strict type checker, YAML and JSON-schema libraries, HTTP client for ASGI tests, OpenTelemetry SDK and in-memory exporter, FastAPI and Pydantic (pinned by `initial_plan.md` §3). Record each chosen tool and its verified version in the `docs/conventions.md` tooling register, tagged `[ASSUMPTION]` for choice and `[SPIKE]` for version. Depends on T001, T005.
- [X] T008 [P] Create root `tests/conftest.py` registering markers `requires_network`, `requires_emulator`, `requires_cloud` and skipping them unless an environment flag is set; unmarked tests must run offline with no credentials.

**Checkpoint**: `uv run pytest -q` collects zero tests and exits cleanly; `uv run ruff check .` and the type checker exit cleanly.

---

## Phase 2: Foundational (blocking prerequisites for every story)

**Purpose**: shared primitives that at least two stories need. No story starts until this phase is green.

### Tests first (RED)

- [X] T009 [P] Create `tests/support/` helpers: `repo_builder.py` (builds a throwaway repo tree in `tmp_path` from a dict), `clock.py` (fixed clock), `secret_shapes.py` (returns secret-shaped strings assembled at call time so no such literal exists in the repository).
- [X] T010 [P] Write `tests/unit/common/test_errors_validation.py`: frozen base model rejects attribute assignment; unknown fields rejected; `validate_at_boundary` raises a typed `BoundaryValidationError` carrying field paths and never echoing rejected values that look like secrets. RED.
- [X] T011 [P] Write `tests/unit/common/test_provenance.py`: the tag vocabulary is exactly `[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]`; parsing rejects any other bracketed tag; `[SPIKE]` is reported as "unverified". RED.
- [X] T012 [P] Write `tests/unit/tools/common/test_findings_cli_report.py`: a `Finding` has file, line, rule id, message; exit codes are 0 for pass, 1 for findings, 2 for tool or config error; the report writer writes a JSON report under `evals/reports/` and never overwrites a report from another tool. RED.
- [X] T013 [P] Write `tests/unit/tools/common/test_yaml_io.py`: safe loading only; malformed YAML and schema violations raise a config error naming file and path, never a traceback-only failure. RED.
- [X] T014 [P] Write `tests/unit/tools/records/test_parsers.py` with fixtures under `tests/fixtures/records/`: parse an ADR file into fields (title, status, date, context, options, decision, consequences, evidence, revisit when); parse a spike file (id, question, time box, owner, outcome, linked ADR, state); parse the ADR index table and the spike table in `docs/spikes_and_adrs.md`; missing sections return explicit "absent" markers rather than empty strings. RED.
- [X] T015 [P] Write `tests/contract/test_schema_copies.py`: each JSON schema in `specs/001-platform-foundations/contracts/` is byte-identical to its copy in `schemas/`, and every copy is a valid JSON Schema document. RED. Purpose: runtime code must not read from `specs/`, and the copies must not drift.

### Implementation (GREEN)

- [X] T016 [P] Implement `src/eios/common/errors.py` (typed error hierarchy rooted at `EiosError`) and `src/eios/common/validation.py` (frozen, extra-forbidden base model; `validate_at_boundary`). Makes T010 pass.
- [X] T017 [P] Implement `src/eios/common/provenance.py`: `Tag` enum of the five tags, `parse_tag`, `is_unverified`. Makes T011 pass.
- [X] T018 [P] Implement `tools/common/findings.py`, `tools/common/cli.py` (exit-code contract 0/1/2, argument base) and `tools/common/report.py`. Makes T012 pass.
- [X] T019 [P] Implement `tools/common/yaml_io.py`: safe load plus schema validation with file and path in every error. Makes T013 pass.
- [X] T020 [P] Implement `tools/records/markdown.py`, `adr.py`, `spike.py`, `index.py`: read-only parsers only (no validation rules; those belong to US5). Makes T014 pass.
- [X] T021 [P] Copy the five JSON schemas (`pipeline-run-record`, `llm-gateway-config`, `llm-call-trace`, `feature-dependencies`, and any other `*.schema.json` in `specs/001-platform-foundations/contracts/`) into `schemas/`. Makes T015 pass.
- [X] T022 Run `uv run pytest tests/unit tests/contract -q`, `uv run ruff check .`, and the type checker; all must be green. This is the gate for starting any story.

**Checkpoint**: foundation ready. US1, US2 and US3 may now start in parallel (all P1). US4 and US5 need only Phase 2 plus their own story. US6 needs US3 (gateway traces) and US2 (environments) for its integration tasks, marked below.

---

## Phase 3: User Story 1 - Every change passes blocking quality gates (Priority: P1) MVP

**Goal**: one definition of every blocking gate, run identically locally and in the pipeline, with hook registries that later features fill in without editing pipeline code.

**Requirements**: FR-003, FR-004, FR-005, FR-006, FR-009, FR-011, FR-012. **Success criteria**: SC-001, SC-002. Contracts: `contracts/gate-hook-registry.md`, `contracts/pipeline-run-record.schema.json`.

**Independent test**: run the `pr` gate set on `tests/fixtures/clean_skeleton/` and see every gate `pass` on the Pipeline Run Record. Apply each overlay in `tests/fixtures/faulty_changes/<gate>/` and see exactly that gate `fail`, the run `failed`, and the gate id plus report reference on the record. With `evals/registry.yaml` empty, see "no suites registered" and a pass; register a failing stub suite and see a fail (quickstart scenario 1).

### Tests first (RED)

- [X] T023 [P] [US1] Write `tests/contract/gates/test_registry.py` from the gate-hook-registry contract: empty registry prints "no suites registered" and passes; a registered suite exiting non-zero fails the gate and the run is `failed`; a suite whose command is missing or not executable fails (never skipped); a suite that does not produce its report file fails; duplicate id, unknown tier or malformed entry fails before any suite runs; entry rules are id "unique, kebab-case", tier one of contract, eval_smoke, red_line, validation, sealed, command "non-empty; resolved relative to the repository root", owner_feature matching `^F[0-9]{2}$`, report "path under `evals/reports/`"; the tier-by-workflow matrix (sealed runs only under `release-candidate`, validation not under `pr`); a sealed suite is not executed by `pr`. RED.
- [X] T024 [P] [US1] Write `tests/contract/gates/test_run_record.py`: records validate against `schemas/pipeline-run-record.schema.json`; states `started → gates_running → (passed | failed)` and `passed → promoted`; "A failed run never transitions to `promoted`"; gate outcome is one of `pass`, `fail`, `skipped_with_reason`, and `skipped_with_reason` requires a non-empty reason; `sbom_ref` "required for release candidates"; `approver` required for `promote-prod-like` and only ever sourced from verified identity claims; `correlation_id` "required"; `commit_ref` falls back to a content hash when no git exists. RED.
- [X] T025 [P] [US1] Write `tests/unit/tools/gates/test_gate_config.py` for `config/gates.yaml`: `blocking` is always true in F00; ids unique; `stage` is one of `pr`, `merge`, `promote`, `release_candidate`; every gate has a `proof_fixture` path that exists; the nine FR-004 gate ids are present (`lint`, `types`, `coverage`, `contract`, `eval_smoke`, `red_line`, `vuln_scan`, `secret_scan`, `iac_plan`); coverage `threshold` is 80 `[TARGET]`. RED.
- [X] T026 [P] [US1] Write `tests/unit/tools/gates/test_runner.py`: gates run from config in order; each outcome and `report_ref` lands on the record; one failing gate does not stop the others from running but the run ends `failed` with exit code 1; a missing gate command is a failure, not a skip; skipping is allowed only as `skipped_with_reason`. RED.
- [X] T027 [P] [US1] Write `tests/unit/tools/gates/test_quarantine.py` (FR-012): a quarantine entry needs a named owner and an expiry or the config is rejected; an expired entry fails the run; a quarantined gate is recorded as `skipped_with_reason` citing the quarantine; the number of quarantined gates is printed in every run summary and written to the record. RED.
- [X] T028 [P] [US1] Write `tests/unit/tools/repo_checks/test_file_size.py`, `test_forbidden_literals.py`, `test_frozen_models.py`, `test_pinned_deps.py`: a file over the 800-line ceiling `[TARGET]` is flagged with path; a pattern from `config/forbidden_literals.yaml` is flagged with file and line unless the path is in that pattern's allowlist; a non-frozen model class under `src/eios` is flagged; a missing lockfile, or a lockfile out of sync with `pyproject.toml`, fails; a version or price pin without a `[SPIKE]` or `[ASSUMPTION]` tag in documents is left to `label_check` (US4) and is not this check's job. RED.
- [X] T029 [P] [US1] Write `tests/unit/tools/gates/test_local_parity.py` (FR-003, FR-004): the ordered gate ids in `.github/workflows/pr.yml` equal the `pr`-stage ids in `config/gates.yaml`, and the list `tools.gates.local` runs equals the same list. RED.
- [X] T030 [P] [US1] Write `tests/integration/test_faulty_changes.py` (SC-001), parametrised over every gate in `config/gates.yaml`: copy `tests/fixtures/clean_skeleton/` to `tmp_path`, run the runner, expect every gate `pass`; apply that gate's overlay from its `proof_fixture`, expect that gate `fail`, run `failed`, gate id and `report_ref` on the record, and no promotion possible. Mark `vuln_scan` with `requires_network` (advisory database). RED.
- [X] T031 [P] [US1] Write `tests/unit/tools/gates/test_sbom.py` (FR-011): every build run writes an SBOM under `evals/reports/sbom/` and sets `sbom_ref`; a release-candidate record without `sbom_ref` is rejected; the SBOM lists every locked dependency. RED.

### Faulty-change proof fixtures (one per gate; all `[P]`)

- [X] T032 [P] [US1] Create `tests/fixtures/clean_skeleton/`: minimal project with `pyproject.toml`, one typed module, one passing test at full coverage, an empty `evals/registry.yaml`, a valid minimal Terraform directory, and a lockfile. Passes all nine gates.
- [X] T033 [P] [US1] Create `tests/fixtures/faulty_changes/lint/`: overlay adding a style violation the linter rejects.
- [X] T034 [P] [US1] Create `tests/fixtures/faulty_changes/types/`: overlay adding a type error the strict checker rejects.
- [X] T035 [P] [US1] Create `tests/fixtures/faulty_changes/coverage/`: overlay adding untested code that drops coverage below 80% `[TARGET]`.
- [X] T036 [P] [US1] Create `tests/fixtures/faulty_changes/contract/`: overlay registering a `contract`-tier suite whose data-contract check is broken (exits non-zero).
- [X] T037 [P] [US1] Create `tests/fixtures/faulty_changes/eval_smoke/`: overlay registering an `eval_smoke`-tier suite that fails.
- [X] T038 [P] [US1] Create `tests/fixtures/faulty_changes/red_line/`: overlay registering a `red_line`-tier suite that fails (proves the Red-Line hook is live with zero real suites).
- [X] T039 [P] [US1] Create `tests/fixtures/faulty_changes/vuln_scan/`: overlay adding a dependency with a published advisory. Choose the dependency at implementation and record its advisory id and the date checked in the fixture's `NOTES.md` `[SPIKE]`.
- [X] T040 [P] [US1] Create `tests/fixtures/faulty_changes/secret_scan/`: overlay built by a `build.py` that writes a secret-shaped string generated by `tests/support/secret_shapes.py` at test time. No such literal is stored in the repository.
- [X] T041 [P] [US1] Create `tests/fixtures/faulty_changes/iac_plan/`: overlay adding an invalid infrastructure definition that `terraform validate` or the linter rejects.

### Implementation (GREEN)

- [X] T042 [US1] Create `config/gates.yaml` with the nine FR-004 gates. Fields per data-model "Quality Gate": `id`, `blocking` (always true), `stage`, optional `threshold` (coverage 80 `[TARGET]`), `proof_fixture` path, `command`. Later stories append rows here; they do not edit code. Makes T025 pass.
- [X] T043 [P] [US1] Create `evals/registry.yaml` as an empty list, with a header comment giving the entry shape from the contract, and `evals/__init__.py`.
- [X] T044 [P] [US1] Implement `tools/gates/registry.py`: load and validate registry entries exactly per the contract rules quoted in T023; malformed registry raises before any suite runs. Part of T023.
- [X] T045 [US1] Implement `tools/gates/runner.py`: tier-by-workflow matrix, "no suites registered" message, missing command and missing report are failures, `skipped_with_reason` handling, run-all-then-fail semantics. Makes T023 and T026 pass. Depends on T044, T046.
- [X] T046 [P] [US1] Implement `tools/gates/run_record.py`: frozen record model, state machine, schema validation against `schemas/pipeline-run-record.schema.json`, content-hash `commit_ref` fallback, writer to `evals/reports/run-records/<run_id>.json`. Makes T024 pass.
- [X] T047 [P] [US1] Implement `tools/gates/quarantine.py` and create `config/quarantine.yaml` (empty list; entries need `gate_id`, `owner`, `expires`, `reason`). Makes T027 pass.
- [X] T048 [P] [US1] Implement `tools/repo_checks/{file_size,forbidden_literals,frozen_models,pinned_deps}.py`, and create `config/repo_checks.yaml` (which checks are enabled; ceiling 800 `[TARGET]`) and `config/forbidden_literals.yaml` (schema only; entries are added in T128). Makes T028 pass.
- [X] T049 [P] [US1] Implement `tools/gates/sbom.py`: invokes the chosen SBOM generator, writes to `evals/reports/sbom/`, returns the reference. Record the tool in the tooling register `[ASSUMPTION]`. Makes T031 pass.
- [X] T050 [US1] Choose and wire the dependency auditor, container and IaC scanner, secret scanner and tflint. Record each in the `docs/conventions.md` tooling register (`[ASSUMPTION]` choice, `[SPIKE]` version). Fill the `command` for `vuln_scan`, `secret_scan`, `iac_plan` in `config/gates.yaml`. The secret scan must cover the working tree, history when one exists, built images and captured logs (SC-004).
- [X] T051 [US1] Implement `evals/cli.py` (`uv run python -m evals.cli run --tier <tier>`): reads `evals/registry.yaml`, runs one tier through `tools/gates/runner.py`. The `contract`, `eval_smoke` and `red_line` gate commands call it.
- [X] T052 [US1] Implement `tools/gates/local.py`: the single local entry point (FR-003). Runs the `pr`-stage gates from `config/gates.yaml` in order, prints one status line per gate, exits 1 on any failure. `make check` calls it. Makes T029 pass.
- [X] T053 [US1] Create `.github/workflows/pr.yml`: one job step per `pr`-stage gate, each running `uv run python -m tools.gates.run_gate <gate-id>` so every gate appears as its own required status check; minimal permissions; uploads the run record and reports; no long-lived cloud credentials. Makes T029 pass.
- [X] T054 [P] [US1] Create `docs/runbooks/branch-protection.md` (FR-005): required status checks equal the gate ids; the only permitted bypass is a `skipped_with_reason` entry on the Pipeline Run Record; quarantine procedure (FR-012) with owner and expiry.
- [X] T055 [US1] Run T023 to T031 until green, including T030 against every overlay. Fix the tool or the fixture, never the test, unless the test is wrong.
- [X] T056 [US1] Write `docs/setup.md` (FR-003): documented setup with one command and the single local check command. Then run one fresh-start dry run from a clean checkout and record the elapsed time against under 30 minutes `[TARGET]` in `docs/evidence/sc-002-setup-dry-run.md` (SC-002). Manual step, cannot be automated.
- [X] T057 [US1] Execute quickstart scenario 1 and record the gate, fixture, outcome and run id for all nine gates in `docs/evidence/sc-001-faulty-change-proof.md` (SC-001).

**Checkpoint**: US1 is the MVP. `make check` runs every blocking gate; every gate is proven to fail on a faulty change and pass on a clean one.

---

## Phase 4: User Story 2 - Isolated, reproducible environments with least-privilege identity (Priority: P1)

**Goal**: `dev`, `stage` and `prod-like` created only from repository contents, isolated from each other, with one identity per service, secrets only in the managed store, and an eval-truth location no runtime identity can read. Also the promotion, sealed-eval and rollback workflows, which need these environments.

**Requirements**: FR-007, FR-008, FR-010, FR-013 to FR-020. **Success criteria**: SC-003, SC-004, SC-009. Entities: Environment, Service Identity.

**Independent test**: quickstart scenarios 3, 4 and 8. Recreate one environment from an empty account with zero manual steps and an empty drift plan; list identities (one per service, each least-privilege); a shared identity in a test change fails review; rotate a secret and see it picked up without a code change; confirm the eval-truth location is unreadable by every service and model identity; promote two revisions and roll back inside the documented bound `[TARGET]`.

**Depends on**: Phase 2, and US1 for the gate runner and run record (T044 to T046).

### Tests first (RED)

- [X] T058 [P] [US2] Write `tests/unit/tools/infra_checks/test_environments.py` against the Environment entity: `name` is one of `dev`, `stage`, `prod-like`; `project_ref` "unique per environment `[ASSUMPTION]`"; `state_prefix` "unique per environment; never shared"; "no credential, bucket or state location is referenced by two environments"; `approval_required` true for `prod-like` promotion only; `budget_thresholds` presence is checked in US6, not here. RED.
- [X] T059 [P] [US2] Write `tests/unit/tools/infra_checks/test_identities.py` against Service Identity: one identity per service and a shared identity fails; `roles` "explicit, non-empty; wildcards and project-wide editor grants rejected"; `can_read_eval_truth` "false for all runtime services; true only for harness and pipeline identities"; `impersonable_by` "required for the release-candidate identity". RED.
- [X] T060 [P] [US2] Write `tests/unit/tools/infra_checks/test_prod_like_policy.py` (FR-015): in `prod-like`, every stateful service module call sets minimum instances of at least 1 and a signing key resource exists in Cloud KMS (real key management, per `initial_plan.md` invariant 5); `dev` and `stage` are exempt. RED.
- [X] T061 [P] [US2] Write `tests/unit/common/test_identity_claims.py` (FR-018): approver and user identity are read only from a verified-claims object; a request body carrying `approver`, `user` or `user_id` is rejected or ignored and never reaches the record; unverified claims raise a typed error; claims are frozen. RED.
- [X] T062 [P] [US2] Write `tests/unit/common/test_untrusted_text.py` (FR-020): external free text is wrapped in a frozen `UntrustedText` value; delimiter-like sequences inside it are escaped; control characters are stripped; a length cap is configurable `[ASSUMPTION]`; there is no implicit conversion to `str`, only an explicitly named accessor; instruction-like content is preserved as data and marked untrusted. RED.
- [X] T063 [P] [US2] Write `tests/unit/common/test_logging_redaction.py` (FR-017): secret-shaped strings from `tests/support/secret_shapes.py` are redacted in log messages, exception text and nested dict payloads before emission. RED.
- [X] T064 [P] [US2] Write `tests/unit/common/test_secret_reader.py` (FR-017): secrets are read at call time through a `SecretSource` protocol (memory source in tests); rotating the value is visible on the next read within the configured refresh interval without a code change; the value never appears in `repr`, `str` or logs; a missing secret raises a typed error naming only the secret name. RED.
- [X] T065 [P] [US2] Write `tests/contract/workflows/test_promotion_workflows.py` (FR-007, FR-008): `promote-stage.yml` triggers only on push to the main line; `promote-prod-like.yml` is manual and bound to a protected environment that requires approval; `release-candidate.yml` is the only workflow that runs `--tier sealed`; every workflow authenticates with federated identity (`id-token: write`) and none uses a stored cloud key; `pr.yml` performs no deploy. RED.
- [X] T066 [P] [US2] Write `tests/unit/tools/gates/test_promote.py`: promotion sets `passed → promoted` only when every gate is `pass` or `skipped_with_reason`; `promote-prod-like` refuses without an `approver` from verified claims; a failed run never promotes; a release candidate refuses without `sbom_ref`; image digests are recorded on the record. RED.
- [X] T067 [P] [US2] Write `tests/integration/test_rollback.py` (FR-010) with a fake deployer: rollback redeploys the previous revision and toggles the configuration flag; elapsed time is written to the run record; rollback with no previous revision fails with a clear error; the time bound is read from `config/rollback.yaml`, never hard-coded. RED.
- [X] T068 [P] [US2] Write `tests/unit/tools/infra_checks/test_terraform_static.py`: every module under `infra/modules/` declares variables and outputs; no literal project id, credential or secret in `infra/`; `eval_truth_store` grants read only to identities with `can_read_eval_truth: true`; `terraform validate` per environment with the backend disabled (mark `requires_network` for provider download). RED.

### Implementation (GREEN)

- [X] T069 [P] [US2] Implement `tools/infra_checks/environments.py`. Makes T058 pass.
- [X] T070 [P] [US2] Implement `tools/infra_checks/identities.py`. Makes T059 pass.
- [X] T071 [P] [US2] Implement `tools/infra_checks/policy.py` and `tools/infra_checks/__main__.py`; choose the Terraform-parsing approach (static HCL parsing library or `terraform show -json` on a plan) and record it in the tooling register `[ASSUMPTION]`. Makes T060 and T068 pass.
- [X] T072 [P] [US2] Implement `src/eios/common/identity_claims.py`. Makes T061 pass.
- [X] T073 [P] [US2] Implement `src/eios/common/untrusted_text.py`. Makes T062 pass.
- [X] T074 [P] [US2] Implement `src/eios/common/logging_redaction.py`. Makes T063 pass.
- [X] T075 [P] [US2] Implement `src/eios/common/secret_reader.py` with the `SecretSource` protocol, an in-memory source, and a Secret Manager source imported lazily. Makes T064 pass.
- [X] T076 [US2] Create `infra/bootstrap/`: versioned state bucket with one prefix per environment, and CI identity federation restricted to this repository. This is the single documented manual exception (research R-05). Write the exact one-time steps and prerequisites in `docs/runbooks/bootstrap.md`.
- [X] T077 [P] [US2] Create `infra/modules/project_baseline/` (required APIs enabled, logging, guardrails).
- [X] T078 [P] [US2] Create `infra/modules/service_identity/`: one service account plus an explicit role list variable; the module rejects wildcard and project-wide editor roles.
- [X] T079 [P] [US2] Create `infra/modules/secret_store/`: managed secret store, plus a Cloud KMS key ring and asymmetric signing key created only when a `signing_key_enabled` variable is true (used by `prod-like`). Note in `docs/conventions.md` that this key ring extends plan.md.
- [X] T080 [P] [US2] Create `infra/modules/eval_truth_store/`: restricted bucket; read access only for the harness and pipeline identities; the release-candidate identity is reachable only by attribute-restricted impersonation from the release-candidate workflow (Constitution VI).
- [X] T081 [P] [US2] Create `infra/modules/evidence_store/`: retention-locked bucket for run records and evidence (FR-009).
- [X] T082 [P] [US2] Create `infra/modules/artifact_registry/`: image repository; images referenced by digest.
- [X] T083 [P] [US2] Create `infra/modules/run_service/`: Cloud Run service wiring with a `min_instances` variable and its service identity.
- [X] T084 [P] [US2] Create `infra/modules/state_stores/`: Firestore for gateway counters and replay cache (used by T125).
- [X] T085 [US2] Create `infra/envs/dev/`, `infra/envs/stage/`, `infra/envs/prod-like/`, each composing the modules above with its own project reference and state prefix; `prod-like` sets `min_instances >= 1` for stateful services and enables the signing key. No environment references another's resources. Depends on T077 to T084.
- [X] T086 [P] [US2] Create `infra/identities.yaml`: one row per service per environment (`skeleton_edge`, `skeleton_core`, `pipeline`, `eval_harness`, `release_candidate`) with `roles`, `can_read_eval_truth`, `impersonable_by`. Read by T070.
- [X] T087 [P] [US2] Create `docs/environments.md`: the documented differences among the three environments (FR-014), the `[ASSUMPTION]` of one isolated cloud project per environment, and how the release-candidate identity is impersonated.
- [X] T088 [US2] Implement `tools/gates/promote.py`. Makes T066 pass.
- [X] T089 [P] [US2] Implement `tools/gates/rollback.py` and create `config/rollback.yaml` (the time bound is set in T100 from the first rehearsal and tagged `[TARGET]`). Makes T067 pass.
- [X] T090 [P] [US2] Create `.github/workflows/promote-stage.yml`: on merge to the main line, promote to `stage`, then run `validation`-tier suites and the lightweight resilience check via `evals.cli` (FR-007).
- [X] T091 [P] [US2] Create `.github/workflows/promote-prod-like.yml`: manual dispatch, protected environment with required approval; the approver is recorded from verified claims (FR-007, FR-018).
- [X] T092 [P] [US2] Create `.github/workflows/release-candidate.yml`: the only workflow that runs `sealed` tier suites, under the attribute-restricted release-candidate identity (FR-008). Makes T065 pass together with T090 and T091.
- [X] T093 [US2] Extend `.github/workflows/pr.yml` with a plan-only job per environment (no apply) under a read-only plan identity, so every change shows its infrastructure plan.
- [X] T094 [US2] Append gate rows `validation` (stage `promote`), `sealed_eval` (stage `release_candidate`) and `resilience` (stage `promote`) to `config/gates.yaml`, each with a `proof_fixture` under `tests/fixtures/faulty_changes/<gate>/`. Create those three fixtures. T030 then covers them with no code change.
- [X] T095 [US2] Append gate row `infra_policy` (stage `pr`, command `uv run python -m tools.infra_checks`) with fixture `tests/fixtures/faulty_changes/infra_policy/` that introduces a shared identity and a wildcard role.
- [X] T096 [US2] Run T058 to T068 until green.

### Evidence (needs real cloud accounts; mark `requires_cloud`)

- [ ] T097 [US2] Apply `infra/bootstrap/` once by hand in each empty account and record exactly what was done in `docs/runbooks/bootstrap.md`.
- [ ] T098 [US2] Quickstart scenario 3 (SC-003): apply `dev`, `stage`, `prod-like` from the repository only; destroy and recreate one; expect zero manual steps and an empty drift report. Record in `docs/evidence/sc-003-recreate.md`.
- [ ] T099 [US2] Quickstart scenario 4 (SC-004): secret scan over tree, history, images and captured logs returns zero findings; one identity per service; a shared identity in a test change fails review; rotate a secret and see it picked up without a code change; the eval-truth location is unreadable by every service and model identity. Record in `docs/evidence/sc-004-secrets-identity.md`.
- [ ] T100 [US2] Quickstart scenario 8 (SC-009, FR-010): promote two revisions to `stage`, roll back to the first, record elapsed time, set the documented bound in `config/rollback.yaml` tagged `[TARGET]`, and write `docs/runbooks/rollback.md`. Save the record in `docs/evidence/sc-009-rollback-rehearsal.md`. This must be done before any `prod-like` promotion.

**Checkpoint**: environments recreate from repository contents alone; promotion, sealed-eval and rollback paths exist and are proven.

---

## Phase 5: User Story 3 - Provider-neutral LLM access with caps, traces and safe degradation (Priority: P1)

**Goal**: one in-process access point for every model call, running on a deterministic stub provider only, with configuration-only model, price and cap values, daily token cap, full tracing, replay-or-unavailable degradation, and no default model.

**Requirements**: FR-021 to FR-028, FR-035 (ADR-002 part), FR-037. **Success criteria**: SC-005, SC-006, SC-011 (ADR-002 part). Contracts: `contracts/llm-gateway-interface.md`, `contracts/llm-gateway-config.schema.json`, `contracts/llm-call-trace.schema.json`. Entities: LLM Gateway Configuration, LLM Call Trace.

**Independent test**: quickstart scenario 5 on the stub provider with no credentials. All four outcomes (`ok`, `replay`, `unavailable`, `cap_reached`) are reachable; an outage with an empty replay store gives `unavailable` and no text; a warmed store gives `replay` with its original timestamp; warnings fire at 50% and 80% `[TARGET]` and the cap blocks at 100% `[TARGET]` with no provider call; every call has a schema-valid trace with no secret-shaped strings; changing model, price or cap by configuration takes effect with no code change; removing a verification tag fails startup; the hard-coded-literal search finds nothing outside `config/` and `providers/`.

**Depends on**: Phase 2 only. Uses `untrusted_text` (T073) and `logging_redaction` (T074) from US2, so run those first or stub them behind their interfaces.

### Contract amendment

- [X] T101 [US3] Amend `specs/001-platform-foundations/contracts/llm-gateway-interface.md` so the behaviour table matches the spec's edge case: when the daily cap is reached, return `replay` if a cached result exists for the request key, otherwise `cap_reached`; in both cases the provider is not called. Add both cases to the "Contract tests" list. The spec governs the contract.

### Tests first (RED)

- [X] T102 [P] [US3] Write `tests/contract/llm_gateway/test_outcomes.py`: with the stub provider, each of `ok`, `replay`, `unavailable`, `cap_reached` is reachable; at the cap, a request with a cached result returns `replay` and one without returns `cap_reached`, and neither calls the provider; usage at 50% and 80% `[TARGET]` returns `ok` plus a warning event and does not block. RED.
- [X] T103 [P] [US3] Write `tests/contract/llm_gateway/test_request_shape.py`: `GatewayRequest` has exactly `prompt_id`, `prompt_version`, `inputs`, `correlation_id`, `caller`; supplying `model`, `price` or `provider` is rejected; `inputs` is a map of string to string; external free text must arrive wrapped by `untrusted_text` or be rejected. RED.
- [X] T104 [P] [US3] Write `tests/contract/llm_gateway/test_outage.py`: provider forced unavailable with an empty replay store gives `unavailable`, `content` null, never any text; with a warmed replay store gives `replay` with non-null `replay_original_at`; the response model has no `guess`, `estimate` or numeric-claim field. RED.
- [X] T105 [P] [US3] Write `tests/contract/llm_gateway/test_cap.py`: 100% of the configured daily cap blocks and no later call reaches the provider that day; the counter rolls over at the day boundary; thresholds come from configuration, not code. RED.
- [X] T106 [P] [US3] Write `tests/contract/llm_gateway/test_trace.py`: one trace per call for every outcome; validates against `schemas/llm-call-trace.schema.json`; `cost` is derived from configured prices and never invented; `prompt_id` and `prompt_version` "must exist in `prompts.lock.json`"; `config_identity` is a hash of the configuration used; no secret-shaped string appears in any trace field. RED.
- [X] T107 [P] [US3] Write `tests/contract/llm_gateway/test_config.py` against `schemas/llm-gateway-config.schema.json`: `model_id` has "no default; startup fails if absent in a deployed environment"; "values lacking a verification tag are rejected at load" with tags limited to `[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]`; `daily_token_cap` "required; warn at 50/80%, block at 100% `[TARGET]`"; changing model, price or cap in a config file changes behaviour with no code change; the committed `stage` and `prod-like` configs fail startup while ADR-002 is open. RED.
- [X] T108 [P] [US3] Write `tests/contract/llm_gateway/test_replay_key.py`: the replay key is a hash of prompt id, prompt version, inputs and configuration identity; changing any one produces a different key; identical requests produce the same key. RED.
- [X] T109 [P] [US3] Write `tests/contract/llm_gateway/test_prompt_lock.py` (FR-037): a prompt id or version absent from `prompts/prompts.lock.json` raises a validation error before any provider call; a prompt file whose content hash differs from the lock entry raises a mismatch error. RED.
- [X] T110 [P] [US3] Write `tests/contract/llm_gateway/test_stores.py`: parametrised over `memory` and `firestore`; `CounterStore.add_tokens(day, count)` returns the running total; `ReplayStore.put` then `get` round-trips content and stored-at; stores hold no secrets. Mark the `firestore` case `requires_emulator`. RED.
- [X] T111 [P] [US3] Write `tests/unit/llm_gateway/test_models.py`: all models frozen; `content` non-null only for `ok` and `replay`; `replay_original_at` non-null only for `replay`; `tokens_in`, `tokens_out` and `latency_ms` non-negative; `trace_id` always present. RED.
- [X] T112 [P] [US3] Write `tests/unit/llm_gateway/test_providers.py` (FR-026, FR-027): the stub provider is deterministic with canned responses and configurable failure; `ProviderUnavailable` is raised on outage or timeout; provider output failing schema validation raises a typed error and is never returned to the caller (treated as untrusted). RED.
- [X] T113 [P] [US3] Write `tests/unit/tools/repo_checks/test_no_hardcoded_llm_literals.py` (SC-006): a search for model identifiers, prices and provider names across `src/`, `services/`, `tools/` finds zero matches outside `config/` and `src/eios/llm_gateway/providers/`; a planted violation is detected with file and line; the ruff banned-API module list equals the vendor-SDK list in `config/open_decisions.yaml`. RED.
- [X] T114 [P] [US3] Write `tests/unit/tools/open_decision_check/test_adr002.py` (FR-035, SC-011): a vendor-SDK import outside `providers/` fails; a model identifier bound in code, config or infrastructure fails; the stub-provider-only tree passes; the rule is lifted only when `config/open_decisions.yaml` says so and the ADR index shows `Accepted`, never by editing the tool. RED.

### Implementation (GREEN)

- [X] T115 [P] [US3] Implement `src/eios/llm_gateway/models.py`: frozen request, response, outcome enum and trace models with the constraints quoted in T102 to T104, T106, T111.
- [X] T116 [P] [US3] Implement `src/eios/llm_gateway/config.py`: load against `schemas/llm-gateway-config.schema.json`; reject any value lacking a verification tag; no default model; deployed-environment startup failure when `model_id` is absent. Makes T107 pass.
- [X] T117 [P] [US3] Implement `src/eios/llm_gateway/caps.py`: daily counter, threshold events at configured percentages, block at 100%. Makes T105 pass.
- [X] T118 [P] [US3] Implement `src/eios/llm_gateway/replay_cache.py`: replay-key hashing and store access. Makes T108 pass.
- [X] T119 [P] [US3] Implement `src/eios/llm_gateway/trace.py`: build and emit one trace per call, redaction first (uses `logging_redaction`). Makes T106 pass.
- [X] T120 [P] [US3] Implement `src/eios/llm_gateway/stores/memory.py` (counter and replay). Makes the `memory` case of T110 pass.
- [X] T121 [P] [US3] Implement `src/eios/llm_gateway/providers/base.py` (`Provider` protocol, `ProviderResult`, `ProviderUnavailable`) and `providers/stub.py`. Makes T112 pass.
- [X] T122 [P] [US3] Implement `src/eios/llm_gateway/prompt_lock.py`; create one sample prompt `prompts/smoke-echo/v1.md` and `prompts/prompts.lock.json` (id, version, content hash). Makes T109 pass. The lock CLI and drift gate come in US6.
- [X] T123 [US3] Implement `src/eios/llm_gateway/gateway.py`: the single `complete()` access point, boundary validation of input and output, cap check, replay-on-outage, `unavailable` never fabricates. Makes T102, T103, T104 pass. Depends on T115 to T122.
- [X] T124 [P] [US3] Create `config/llm_gateway.dev.yaml` (stub provider, a stub-only model identifier, illustrative cap, every value with a verification tag) and `config/llm_gateway.stage.yaml` and `config/llm_gateway.prod-like.yaml` (same shape, `model_id` deliberately absent, values tagged `[SPIKE]` until S-01 closes). Note in each file that the omission is intentional (FR-028, ADR-002 open).
- [X] T125 [P] [US3] Implement `src/eios/llm_gateway/stores/firestore.py` and create `docker-compose.dev.yml` running the Firestore emulator for the `requires_emulator` tests. Makes the `firestore` case of T110 pass.
- [X] T126 [US3] Implement `tools/open_decision_check/{engine.py,rules.py,__main__.py}`: config-driven rule engine reading `config/open_decisions.yaml` and the ADR index through `tools/records/`; produces file-and-line findings. Only the ADR-002 rule set is exercised here; US5 adds ADR-003, 009 and 014 as config. Makes T114 pass.
- [X] T127 [P] [US3] Create `config/open_decisions.yaml` with the ADR-002 section: `vendor_sdk_modules` (SDK import roots known at implementation, completed when S-01 closes `[SPIKE]`), `model_identifier_patterns`, and `allowed_paths` (`src/eios/llm_gateway/providers/`, `config/`). The four-decision structure (`adr`, `rules`, `allowed_paths`, `lifted_when`) is fixed now so US5 only adds sections.
- [X] T128 [US3] Fill the `banned-api` table in `pyproject.toml` from the `vendor_sdk_modules` list in `config/open_decisions.yaml`, and add the hard-coded-literal patterns (model identifiers, price shapes, provider names) to `config/forbidden_literals.yaml` with allowed paths `config/` and `src/eios/llm_gateway/providers/`. Makes T113 pass.
- [X] T129 [US3] Append gate row `open_decision_check` (stage `pr`, command `uv run python -m tools.open_decision_check`) to `config/gates.yaml` with fixture `tests/fixtures/faulty_changes/open_decision_check/` that plants a vendor-SDK import outside `providers/`.
- [X] T130 [US3] Run T102 to T114 until green, and run T030 to confirm the new gate rows fail on their overlays.
- [X] T131 [US3] Execute quickstart scenario 5 (SC-005, SC-006) and record results, including one captured trace per outcome, in `docs/evidence/sc-005-006-gateway.md`.

**Checkpoint**: the gateway works end to end on the stub provider; no model, price or provider name exists outside configuration and `providers/`.

---

## Phase 6: User Story 4 - Labels and provenance are enforced, not optional (Priority: P2)

**Goal**: a machine-checkable provenance convention and a blocking review-time check that flags unlabelled numeric claims, `[BRIEF]` claims without a brief citation, `[SPIKE]` claims without a valid spike id (reporting that spike's state), generator or eval-origin claims without their references, forbidden literals (competitor brands, unverified version or price pins, secret-shaped strings), and allowlist entries with no reason.

**Requirements**: FR-029, FR-030, FR-031. **Success criteria**: SC-007. Contract: `contracts/provenance-labels.md`. Entity: Provenance Label.

**Independent test**: quickstart scenario 6. `label_check` over the F00 documents passes and prints a scanned-file count; over the seeded document it flags every planted defect (unlabelled figure, `[BRIEF]` without citation, `[SPIKE]` without spike id, generator claim without seed, revision and dataset hash, competitor brand, version pin) with file and line at 100% recall `[TARGET]` and zero false positives on the clean fixture; an allowlist entry with an empty reason is rejected; the same documents pass once corrected.

**Depends on**: Phase 2 (tag enum, findings, CLI, records parser) and US1 (gate runner and `config/gates.yaml`). Independent of US2, US3 and US5, except that the `[SPIKE]` state report reads spike files through `tools/records/` (a fixture spike is used until US5 creates the real ones).

### Tests first (RED)

- [X] T132 [P] [US4] Write `tests/unit/tools/label_check/test_labels_config.py` for `config/labels.yaml`: the tag set is exactly `[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]` and equals the `Tag` enum in `src/eios/common/provenance.py` (drift test); each tag lists its required evidence per the contract table (`[BRIEF]` citation to brief file and section; `[ASSUMPTION]` owner and a verify-by note or spike id; `[ILLUSTRATIVE]` none, and must never feed a metric or a shown KPI; `[TARGET]` metric name and where it will be reported; `[SPIKE]` spike id `S-NN`); a configuration with an extra or missing tag fails to load. RED.
- [X] T133 [P] [US4] Create fixtures under `tests/fixtures/label_check/`: `clean/` (documents that carry every figure correctly: each tag, a citation into a fixture brief, a generator-run reference, an eval-report reference) and `seeded/` (one document per defect class, plus `expected.json` listing the exact file, line and rule id of every planted defect). Brand names and secret-shaped strings are never typed into fixtures: the seeded document contains placeholders (`{{BRAND}}`, `{{SECRET}}`) that the tests replace at run time with a value drawn from `config/forbidden_literals.yaml` and `tests/support/secret_shapes.py`.
- [X] T134 [P] [US4] Write `tests/unit/tools/label_check/test_numeric_claims.py` (FR-030): a table of positives and negatives. Positives (must be flagged when untagged, with file, line and literal): a bare percentage, a currency amount, a count with a unit, a duration, a ratio. Negatives (never flagged): identifiers (`FR-001`, `SC-007`, `T001`, `S-01`, `ADR-002`, `F00`), ISO dates, numbered list markers, heading numbers, line references, fenced code blocks, and anything matched by the `non_claim_patterns` listed in `config/labels.yaml`. A figure carrying exactly one tag in the same sentence, table row or list item (the `claim_scope` rule in `config/labels.yaml`) passes; two tags on one figure fails; a tag not in `config/labels.yaml` fails. RED.
- [X] T135 [P] [US4] Write `tests/unit/tools/label_check/test_brief_citation.py` (acceptance scenario 2): a `[BRIEF]` claim must carry a citation of the form `docs/brief/<file>` plus a section; the file must exist; a citation to a missing file or without a section fails with the claim's location. RED.
- [X] T136 [P] [US4] Write `tests/unit/tools/label_check/test_spike_reference.py` (acceptance scenario 3): a `[SPIKE]` claim must carry an id matching `^S-[0-9]{2}$`; an id with no spike record fails; a valid id passes and the report line states whether that spike is `open` or `closed`, read through `tools/records/spike.py` from a fixture spike record. RED.
- [X] T137 [P] [US4] Write `tests/unit/tools/label_check/test_origin_references.py` (acceptance scenario 4): a figure claiming a generator origin must carry seed, code revision and dataset hash (all three); a figure claiming an evaluation origin must carry a path under `evals/reports/`; a missing element, or a path outside `evals/reports/`, fails naming which element is missing. RED.
- [X] T138 [P] [US4] Write `tests/unit/tools/label_check/test_forbidden_and_allowlist.py` (FR-031): a competitor brand used as a competitor, a version-shaped string next to a tool, model or price word without a tag, and a secret-shaped string are each flagged with file and line. Allowlist behaviour per `config/label_allowlist.yaml`: an entry with an empty or whitespace reason is rejected as a config error; an entry whose file or literal no longer exists is reported as stale; an entry silences only its own path and literal. RED.
- [X] T139 [P] [US4] Write `tests/unit/tools/label_check/test_scope_report_cli.py`: scope globs come from `config/labels.yaml`; the prototype paths `FEIOS/`, `DESIGN.MD`, `DESIGN_PLAN.md` are excluded by configuration and listed in the report; `docs/brief/` is treated as source, not scanned for claims; a clean run prints the scanned-file count; exit codes are 0 pass, 1 findings, 2 config error; the report is written to `evals/reports/label_check.json`. RED.
- [X] T140 [P] [US4] Write `tests/integration/test_label_check_seeded_recall.py` (SC-007): run `label_check` over `tests/fixtures/label_check/seeded/`; compute recall against `expected.json` and assert 1.0 (100% `[TARGET]`); run over `clean/` and assert zero findings. RED.
- [X] T141 [P] [US4] Write `tests/unit/tools/label_check/test_structured_config_tags.py`: for the `structured_rules` in `config/labels.yaml`, every numeric leaf of `config/llm_gateway.*.yaml` requires a sibling verification tag and every row of `docs/cost_model.csv` requires a `tag` value (price, source and date rules stay with `cost_check`, T207); removing a tag from a gateway config value fails `label_check` and also fails the gateway config loader (T116), proving the two agree. RED.
- [X] T142 [P] [US4] Write `tests/integration/test_label_check_f00_docs.py` (SC-007, scenario 6 step 1): run `label_check` over the F00 governed documents named in `config/labels.yaml` and assert zero findings and a non-zero scanned-file count. RED until T151 completes the remediation.

### Implementation (GREEN)

- [X] T143 [P] [US4] Create `config/labels.yaml`: the five tags and their evidence rules; `claim_scope` (sentence, table row, list item); `non_claim_patterns` (identifiers, ISO dates, list and heading numbers, line references); governed scope (`specs/**/*.md`, `docs/**/*.md` except `docs/brief/`, `docs/evidence/**`, `evals/reports/` text reports excluded); excluded prototype paths; `structured_rules` for `config/llm_gateway.*.yaml` and `docs/cost_model.csv`. Makes T132 pass.
- [X] T144 [P] [US4] Create `config/label_allowlist.yaml` (empty list, schema in the header comment) and extend `config/forbidden_literals.yaml` (created in T048, extended in T128) with the competitor-brand class (list maintained in the file; the file itself is a declared exempt path for `label_check` with a stated reason, so no brand literal appears anywhere else), the version-pin class (version-shaped strings next to tool, model or price words) and the secret-shape class shared with the secret-scan gate.
- [X] T145 [P] [US4] Implement `tools/label_check/rules.py`: numeric-claim detection, claim-scope resolution, tag counting, non-claim exclusion. Makes T134 pass.
- [X] T146 [P] [US4] Implement `tools/label_check/citations.py`: brief citation resolver (file exists, section present), spike resolver (reads `tools/records/spike.py`, reports state), origin-reference parsers (generator: seed, revision, dataset hash; eval: path under `evals/reports/`). Makes T135, T136, T137 pass.
- [X] T147 [P] [US4] Implement `tools/label_check/allowlist.py`: load, reason-required validation, stale-entry detection, per-path and per-literal matching. Part of making T138 pass.
- [X] T148 [US4] Implement `tools/label_check/scanner.py` and `tools/label_check/__main__.py`: file walk from configured scope, Markdown and structured-file handling, forbidden-literal pass, report writing, exit-code contract, scanned-file count. Makes T138, T139, T140, T141 pass. Depends on T143 to T147.
- [X] T149 [P] [US4] Extend `docs/conventions.md` with the provenance convention (FR-029): one worked example per tag, how to attach a brief citation, a generator-run reference (seed, code revision, dataset hash) and an evaluation-report reference, how `label_check` reads `claim_scope`, and how to request an allowlist entry (reason required, reviewed).
- [X] T150 [US4] Append gate row `label_check` (stage `pr`, command `uv run python -m tools.label_check`) to `config/gates.yaml` with fixture `tests/fixtures/faulty_changes/label_check/` (an unlabelled figure in a governed document). T030 then covers it with no code change.
- [X] T151 [US4] Run `label_check` over the F00 governed documents and fix every finding in the documents themselves (add the correct tag or evidence). Do not narrow the scope, widen `non_claim_patterns` beyond identifiers, or add allowlist entries to make findings disappear; any allowlist entry added carries a reviewed reason. Makes T142 pass.
- [X] T152 [US4] Run T132 to T142 until green, and run T030 to confirm the `label_check` gate fails on its overlay and passes on the clean skeleton.
- [X] T153 [US4] Execute quickstart scenario 6 (SC-007), including the empty-reason allowlist rejection, and record results in `docs/evidence/sc-007-labels.md` with the recall figure and the scanned-file count.

**Checkpoint**: unlabelled or untraceable figures cannot reach `main`; the seeded document is caught at 100% recall `[TARGET]`.

---

## Phase 7: User Story 5 - Decisions and spikes have a durable, enforceable record (Priority: P2)

**Goal**: ADR and spike templates in `docs/adr/`, a single status index that must agree with the records, feature dependency declarations with a readiness check that blocks on open spikes, unaccepted ADRs and incomplete features, and an open-decision check that keeps ADR-002, 003, 009 and 014 open by flagging any artefact that fixes their outcome.

**Requirements**: FR-032, FR-033, FR-034, FR-035. **Success criteria**: SC-008, SC-011. Contract: `contracts/decision-and-spike-records.md`, `contracts/feature-dependencies.schema.json`. Entities: Decision Record, Spike Record, Feature Dependency Declaration.

**Independent test**: quickstart scenario 7. `adr_check` agrees on the real index and files and fails on each planted mismatch class; a feature declaring a dependency on an open spike is reported blocked and the spike is named, in 100% of test cases `[TARGET]`; closing the spike with an accepted ADR makes `readiness` report ready on the next run; `open_decision_check` reports ADR-002, 003, 009 and 014 still open with no F00 artefact fixing their outcome, and fails on each planted vendor SDK import, metric-engine manifest, frontend manifest and API route.

**Depends on**: Phase 2 (records parsers), US1 (gate runner), and US3 (`open_decision_check` engine T126 and `config/open_decisions.yaml` structure T127). Independent of US2, US4 and US6.

### Contract amendment

- [X] T154 [US5] Amend `specs/001-platform-foundations/contracts/decision-and-spike-records.md` and copy any changed schema to `schemas/`, so the contract matches `research.md` R-14, `data-model.md` sections 8, 9 and 11, and the spec's acceptance scenarios (the spec and data model govern). Amendments: (a) `Proposed` and `Open` entries may lack a record file; `Accepted` and `Superseded` require one, so index-without-file fails only for those two; (b) Evidence may be a design-document reference under `docs/` or `initial_plan.md` for records backfilled from decisions taken before F00, marked as backfilled; (c) a spike record carries question, time box `[TARGET]`, owner, state, and, to close, method, data, result, decision, date, outcome and linked ADR; (d) each feature declares its dependencies in `specs/<feature-dir>/dependencies.yaml` conforming to `feature-dependencies.schema.json`, and `docs/feature_register.yaml` lists every feature id with a `complete` flag.

### Tests first (RED)

- [X] T155 [P] [US5] Create fixtures under `tests/fixtures/decisions/`: a valid index plus ADR files and spike records, and one broken variant per failure class (index entry with no file for an `Accepted` record; file with no index entry; status mismatch; duplicate number; one-way supersession; missing required field; `Accepted` without evidence; fewer than two options; closed spike without linked ADR; closed spike linking an `Open` ADR), plus `dependencies.yaml` and `feature_register.yaml` variants for readiness (blocked on spike, on ADR, on feature; ready).
- [X] T156 [P] [US5] Write `tests/unit/tools/adr_check/test_adr_fields.py` (FR-034): title is `ADR-NNN: <text>` with the number equal to the filename's; status is one of `Proposed`, `Accepted`, `Superseded by ADR-XXX`; date is ISO `YYYY-MM-DD`; context non-empty; "options considered: at least two"; decision non-empty when `Accepted` or `Superseded`; consequences non-empty; evidence "required when `Accepted`"; revisit-when non-empty. Each violation fails with file and field. RED.
- [X] T157 [P] [US5] Write `tests/unit/tools/adr_check/test_index_agreement.py` (FR-034, acceptance scenario 4): the index in `docs/spikes_and_adrs.md` and the files agree on number, title and status; each class from T155 fails with a distinct message; `Proposed` and `Open` without a file pass (T154a); supersession must be bidirectional (the successor names the replaced ADR and the replaced ADR names its successor). RED.
- [X] T158 [P] [US5] Write `tests/unit/tools/adr_check/test_spike_rules.py`: Id matches `^S-[0-9]{2}$`; question, time box and owner are non-empty; a spike cannot close without a linked ADR; the linked ADR must exist in the index and not be `Open`; a closed spike requires method, data, result, decision, date and outcome (T154c); an open spike needs only question, time box, owner. RED.
- [X] T159 [P] [US5] Write `tests/unit/tools/readiness/test_readiness.py` (FR-033, SC-008): blocked and the spike named when a `depends_on_spikes` entry is open; blocked and the ADR named when a `depends_on_adrs` entry is not `Accepted`; blocked and the feature named when a `depends_on_features` entry is not marked complete in `docs/feature_register.yaml`; ready when all hold; every unmet dependency is listed with its current state; exit 0 when ready, 1 when blocked, 2 on config error; a `dependencies.yaml` violating `schemas/feature-dependencies.schema.json` is a config error; changing the spike's fixture to closed with an `Accepted` ADR flips the result on the next run. RED.
- [X] T160 [P] [US5] Write `tests/unit/tools/open_decision_check/test_adr003_009_014.py` (FR-035, SC-011): ADR-003 flags a metric-engine package in a manifest or lockfile, a metric-engine schema file, or a metric-engine import; ADR-009 flags a frontend-framework manifest or a design-system dependency; ADR-014 flags a GraphQL schema file or a business-resource route (the skeleton health and forward routes in `allowed_paths` pass); spec-text rule: a specification sentence that states one of the four decisions as settled (decisive verb with a candidate name and no "candidate", "option" or "open" qualifier) is flagged, while the same candidate named as an option passes; prototype paths `FEIOS/`, `DESIGN.MD`, `DESIGN_PLAN.md` are excluded by configuration and listed; a rule lifts only when `config/open_decisions.yaml` `lifted_when` is satisfied and the index shows `Accepted`; all four ADRs report "open" on the clean tree. RED.
- [X] T161 [P] [US5] Write `tests/unit/tools/records/test_templates.py` (FR-032, acceptance scenarios 1 and 2): `docs/adr/_template-adr.md` contains every ADR field heading from T156; `_template-spike.md` contains every spike field from T158; a record created by copying a template and filling every field passes `adr_check`; a template copied and left unfilled fails with the empty-field messages. RED.
- [X] T162 [P] [US5] Write `tests/unit/tools/decisions/test_cli_reports.py`: `adr_check`, `readiness` and `open_decision_check` each use the exit-code contract 0 pass, 1 findings, 2 config error, and write `evals/reports/<tool>.json`. RED.
- [X] T163 [P] [US5] Write `tests/integration/test_real_decision_records.py` (SC-011): over the real repository, `adr_check` passes; ADR-002, 003, 009 and 014 are `Open` in the index with no record file; every `Accepted` row in the index has a record file; spike records exist for S-01 to S-07 and all are `open`; `open_decision_check` passes with all four reported open. RED until T169 to T175 are done.

### Implementation (GREEN)

- [X] T164 [P] [US5] Create `docs/adr/_template-adr.md` and `docs/adr/_template-spike.md` matching the templates in `docs/spikes_and_adrs.md` and the amended contract (T154): every required field present as a heading with a one-line instruction, a status line listing the allowed values, an options section that asks for an honest drawback per option, and the evidence line. Makes T161 pass.
- [X] T165 [P] [US5] Implement `tools/adr_check/{validate.py,agreement.py,__main__.py}`: field validation (T156, T158), index-versus-files agreement and supersession (T157), exit-code contract, report. Uses the read-only parsers in `tools/records/`. Makes T156, T157, T158 and the `adr_check` part of T162 pass.
- [X] T166 [P] [US5] Implement `tools/readiness/{engine.py,__main__.py}`: load `specs/*/dependencies.yaml` (validated against `schemas/feature-dependencies.schema.json`), resolve states through `tools/records/` and `docs/feature_register.yaml`, print each unmet dependency with its state, usage `uv run python -m tools.readiness F03`. Makes T159 and the `readiness` part of T162 pass.
- [X] T167 [US5] Extend `tools/open_decision_check/rules.py` (engine from T126) with the rule kinds ADR-003, 009 and 014 need, all config-driven: `manifest_dependency`, `file_pattern`, `route_definition` and `spec_text`, plus the prototype-path exclusion. No decision-specific logic in code. Makes T160 and the `open_decision_check` part of T162 pass.
- [X] T168 [P] [US5] Extend `config/open_decisions.yaml` (structure fixed in T127) with the ADR-003, ADR-009 and ADR-014 sections (`adr`, `rules`, `allowed_paths`, `lifted_when`) and a top-level `spec_text` section. Candidate names come from `docs/spikes_and_adrs.md` S-02, S-03 and ADR-014. `allowed_paths` for ADR-014 is only the health and forward routes in `services/skeleton_edge/app.py` and `services/skeleton_core/app.py`. Excluded paths: `FEIOS/`, `DESIGN.MD`, `DESIGN_PLAN.md`.
- [X] T169 [P] [US5] Backfill `docs/adr/001-ontology-as-data-logic-action-security.md` from the ADR-001 index row and `docs/foundry.md`: status `Accepted`, the options and their honest drawbacks as recorded in the sources, evidence a design-document reference marked backfilled, a revisit-when trigger. Add no fact absent from the sources; where a source lacks a drawback, write the drawback as `[ASSUMPTION]` with an owner and a verify-by note.
- [X] T170 [P] [US5] Backfill `docs/adr/006-action-intent-signing.md` and `docs/adr/007-ledger-tamper-evidence.md` from their index rows, `docs/red_team_findings_v3.md` (why HMAC was replaced) and spike S-06 (verification only): status `Accepted`, evidence marked backfilled, S-06 linked as pending verification. Same sourcing rule as T169.
- [X] T171 [P] [US5] Backfill `docs/adr/010-approval-service-runtime.md`, `011-simulated-write-back-sink.md`, `012-warm-start-and-state-strategy.md` and `013-streaming-batch-separation.md` from their index rows and `initial_plan.md` (invariant 3 for ADR-013; S-05 for ADR-012). Same sourcing rule as T169.
- [X] T172 [P] [US5] Backfill `docs/adr/015-synthetic-data-split-policy.md` from the index row and `docs/synthetic_data_strategy.md`. Same sourcing rule as T169.
- [X] T173 [P] [US5] Create open spike records `docs/adr/S-01-llm-availability-and-pricing.md` through `S-07-entity-resolution-approach.md` from the rows in `docs/spikes_and_adrs.md` section 1: question, method, owner, time box (the source states "at most 1 day `[ASSUMPTION]` unless stated"; copy any per-spike override), state `open`, linked ADR as the "decision it unlocks" column. Do not invent results.
- [X] T174 [P] [US5] Create `docs/feature_register.yaml` listing F00 to F15 from `initial_plan.md` section 12, each with `complete: false` (F00 flips at the end of Phase 9), and `specs/001-platform-foundations/dependencies.yaml` declaring feature F00 with empty `depends_on_features`, `depends_on_spikes` and `depends_on_adrs` (F00 runs on the stub provider and needs no open decision).
- [X] T175 [US5] Update the index in `docs/spikes_and_adrs.md` so each `Accepted` row links its record file and each spike row links its spike record; change no status. Depends on T169 to T173.
- [X] T176 [US5] Append gate row `adr_check` (stage `pr`, command `uv run python -m tools.adr_check`) to `config/gates.yaml` with fixture `tests/fixtures/faulty_changes/adr_check/` (index row marked `Accepted` with no record file). T030 then covers it with no code change. The `open_decision_check` row already exists (T129).
- [X] T177 [US5] Run T155 to T163 until green, and run T030 to confirm the `adr_check` gate fails on its overlay and passes on the clean skeleton.
- [X] T178 [US5] Execute quickstart scenario 7 (SC-008, SC-011): the mismatch classes, readiness blocked then ready after a fixture spike closes with an `Accepted` ADR, and the planted vendor SDK import. Record results in `docs/evidence/sc-008-011-decisions.md`, including the four open ADRs shown open.

**Checkpoint**: no decision can be made by accident; a feature cannot start on an unresolved spike; ADR-002, 003, 009 and 014 are provably still open.

---

## Phase 8: User Story 6 - Observability and cost visibility from day one (Priority: P3)

**Goal**: two skeleton services that carry one correlation identifier across a service boundary in traces and logs, an SLO placeholder, runbook stub and warm-start statement per service, versioned prompts with a lock CLI and drift gate, a component-level cost model checked by `cost_check`, and budget alerts at 50%, 80% and 100% `[TARGET]` wired into every environment, with a dev-only trigger.

**Requirements**: FR-036, FR-037, FR-038, FR-039. **Success criteria**: SC-010. Contract: `contracts/cost-model.md`. Entities: Cost Model Row, Service Skeleton, LLM Call Trace (prompt reference).

**Independent test**: quickstart scenario 9. One request through `skeleton_edge` to `skeleton_core` shows the same correlation identifier in both services' traces and logs; each skeleton has an SLO placeholder, runbook stub and warm-start statement; `cost_check` passes with totals over verified rows only and every figure showing source, pricing date and label; each environment's infrastructure plan contains the three budget thresholds; one threshold triggered in `dev` raises the alert.

**Depends on**: US1 (gate runner, container scan), US2 (`run_service`, `artifact_registry` and environment compositions T082, T083, T085), US3 (`logging_redaction`, trace builder, prompt lock T122, gateway configs), US4 (`label_check` governs the cost file and the docs added here), US5 (not required). The correlation tests and the cost-model tests need nothing from US2.

### Contract amendment

- [ ] T179 [US6] Amend `specs/001-platform-foundations/contracts/cost-model.md` so it covers FR-038 completely (the spec governs): (a) add an optional `reconciliation` column, value `pending` or `reconciled:<bill reference>`, defaulting to `pending`, because the contract requires "reconciliation against the actual bill ... recorded as a status on each row once a bill exists" but its column table has no place for it; (b) a driver named `total` or `subtotal` (any case) is rejected, so no hand-typed total can exist; (c) the staleness threshold, the gateway-to-driver linkage map and the budget thresholds live in configuration, naming `config/cost_linkage.yaml` and `config/budgets.yaml` and their keys; (d) the check also fails when a configured budget threshold is missing from any environment's plan.

### Tests first (RED)

- [ ] T180 [P] [US6] Create fixtures under `tests/fixtures/cost_model/`: a clean file and one file per failure row of the contract (price without `price_source`; price without `price_verified_on`; missing tag; tag outside the five; `[SPIKE]` row whose `price_source` has no spike id; stale `price_verified_on`; duplicate driver; negative quantity; non-ISO date; driver named `Total`; blank price; unknown `reconciliation` value), plus matching and mismatching gateway configuration fixtures and a linkage map. Prices in fixtures are placeholders marked `[ILLUSTRATIVE]` in a README beside them.
- [ ] T181 [P] [US6] Write `tests/unit/tools/cost_check/test_rules.py` (FR-038): each situation in the contract's checker table gives the stated result, including "Row has unit_price but no price_source or price_verified_on: fail", "Row tag missing or not one of the five: fail", "Row tagged `[SPIKE]` without a spike id in price_source: fail", "Duplicate driver: fail", and the stale date as a warning only, never a failure; the staleness threshold is read from `config/cost_linkage.yaml`, not from code. Findings carry file, line and driver. RED.
- [ ] T182 [P] [US6] Write `tests/unit/tools/cost_check/test_totals_report.py` (acceptance scenario 4): totals are computed by the tool over verified rows only (`quantity` and `unit_price` both set); rows with a blank price are reported "unverified" and excluded; the printed report shows for every figure its source, pricing date and tag; the report never contains a figure that is not derived from a row; exit codes 0 pass, 1 findings, 2 config error; report written to `evals/reports/cost_check.json`. RED.
- [ ] T183 [P] [US6] Write `tests/unit/tools/cost_check/test_linkage.py`: for each gateway configuration named in `config/cost_linkage.yaml`, the configured token price for a model must equal the unit price of the linked driver row; a mismatch fails and names both values and files; a gateway price with no linked row fails; a linked row with no gateway price passes; a changed linkage key is a config error. RED.
- [ ] T184 [P] [US6] Write `tests/unit/common/test_correlation.py` (FR-036): `new_correlation_id()` returns an opaque non-empty string with no embedded personal or host data; an inbound identifier is accepted only if it matches the pattern fixed in `src/eios/common/correlation.py` (length bound set at implementation `[ASSUMPTION]`, characters limited to letters, digits and hyphen); an over-long, empty or control-character value is replaced and never reflected into logs or headers (log injection); the header name is a single constant; `current_id()` is isolated per concurrent task (two concurrent async tasks never see each other's id); outbound helper adds the header from the current id; the module exposes immutable values only. RED.
- [ ] T185 [P] [US6] Write `tests/unit/common/test_otel.py`: with an in-memory exporter, every span carries `correlation_id`; every structured log record carries `correlation_id`; log messages pass through `logging_redaction` (a secret-shaped string from `tests/support/secret_shapes.py` is redacted); the exporter endpoint and service name come from environment variables and no endpoint literal exists in code; with no endpoint configured, setup installs a no-op exporter and does not raise; calling setup twice does not duplicate handlers. RED.
- [ ] T186 [P] [US6] Write `tests/contract/services/test_skeleton_routes.py` (constitution II, plan gate G2): the OpenAPI document of each skeleton lists exactly the health route and its one correlation route (`skeleton_edge`: health and forward; `skeleton_core`: health and echo), only `GET`; any `POST`, `PUT`, `PATCH` or `DELETE` is absent and answers 405; no route returns a business metric; health answers without touching other services. RED.
- [ ] T187 [P] [US6] Write `tests/integration/test_correlation_end_to_end.py` (SC-010, acceptance scenario 1): mount `skeleton_core` behind an in-process ASGI transport and call `skeleton_edge`; with no inbound identifier a new one is generated and appears in the edge span, the core span, both services' log records and the response header; a valid supplied identifier is preserved in all four places; an invalid one is replaced and the replacement is identical in both services; when core fails, the edge returns an error body and header carrying the same identifier and logs it; spans from both services share one trace. RED.
- [ ] T188 [P] [US6] Write `tests/unit/tools/repo_checks/test_service_docs.py` (FR-039): each directory under `services/` must hold non-empty `slo.md`, `runbook.md` and `warm_start.md`; `slo.md` has the fields indicator, objective, owner feature and status, with status `placeholder` accepted and any objective figure requiring a provenance tag; `runbook.md` has the sections symptoms, first checks, escalation and rollback; `warm_start.md` states `holds in-memory state: yes` or `no` and, when `yes`, a non-empty warm-up behaviour; a missing, empty or sectionless file fails with the service and file. RED.
- [ ] T189 [P] [US6] Write `tests/unit/tools/prompt_lock/test_prompt_lock_cli.py` (FR-037): `check` fails naming prompt id and version when a locked prompt file's content hash differs from the lock; fails on a prompt file present but absent from the lock; fails on a lock entry with no file; fails when a locked version is deleted; `update` adds a new `v<N>.md` to the lock and never rewrites the hash of an existing version (existing versions are immutable, an edited `v1.md` must be a new `v2.md`); output is byte-stable and sorted so the lock diff is reviewable; exit codes 0, 1, 2. RED.
- [ ] T190 [P] [US6] Write `tests/integration/test_prompt_version_in_trace.py` (acceptance scenario 2): on a temporary copy of `prompts/`, call the gateway with the stub provider for `smoke-echo` `v1` and see `prompt_version` `v1` in the trace; add `v2` through the CLI and call again, the trace shows `v2` and the replay key differs from the `v1` key; `v1` remains callable; a call naming a version not in the lock is rejected before any provider call. RED.
- [ ] T191 [P] [US6] Write `tests/unit/tools/infra_checks/test_budget_alerts.py` (FR-038, acceptance scenario 3): the thresholds in `config/budgets.yaml` must include 50, 80 and 100 `[TARGET]` and be percentages in ascending order; each environment composition under `infra/envs/` passes every configured threshold to `budget_alerts` and none is a literal in `infra/`; the module has no default for thresholds or amount; a notification channel resource is declared in infrastructure code; each environment has a budget amount in `config/budgets.yaml` carrying a provenance tag; removing a threshold from one environment fails with the environment named. RED.
- [ ] T192 [P] [US6] Write `tests/unit/tools/budget_probe/test_probe.py` and `tests/integration/test_budget_alert_dev.py` (marked `requires_cloud`): the probe builds a budget notification payload for a chosen threshold; it refuses any environment other than `dev`; `--dry-run` prints the payload and publishes nothing; publishing goes through an injected publisher (fake in unit tests); the cloud test publishes one threshold to `dev` and asserts the alert is delivered to the channel declared in infrastructure code. RED.
- [ ] T193 [P] [US6] Write `tests/integration/test_real_observability_and_cost.py` over the real repository: `cost_check` passes on `docs/cost_model.csv` with every row tagged; the gateway-to-driver linkage resolves for all three gateway configurations; every `services/*` passes the T188 checks; `prompt_lock check` passes; `config/budgets.yaml` holds the three thresholds for each of `dev`, `stage`, `prod-like`. RED until T200 to T216 are done.

### Implementation (GREEN)

- [ ] T194 [US6] Add the runtime dependencies for the skeleton services (ASGI web framework, HTTP client, telemetry API and SDK) to `pyproject.toml` by role, run `uv lock`, and record each choice in the `docs/conventions.md` tooling register (`[ASSUMPTION]` choice, `[SPIKE]` version). Add a ruff banned-import entry so telemetry SDK classes are imported only in `src/eios/common/otel.py`.
- [ ] T195 [P] [US6] Implement `src/eios/common/correlation.py`: identifier generation, validation, header constant, context-local storage, outbound header helper. Makes T184 pass.
- [ ] T196 [P] [US6] Implement `src/eios/common/otel.py`: setup function taking service name, wiring tracer, the structured log handler that adds `correlation_id` and applies `logging_redaction`, and exporter selection from environment variables with a no-op fallback. Makes T185 pass.
- [ ] T197 [P] [US6] Implement `services/skeleton_core/app.py` (health route and one echo route that returns the correlation identifier it received; middleware that reads or creates the id, starts a span, logs) and `services/skeleton_core/Dockerfile` (non-root user, no secrets in layers, image built from `uv.lock`, port and service name from environment). Part of making T186 and T187 pass.
- [ ] T198 [P] [US6] Implement `services/skeleton_edge/app.py` (health route and a forward route that calls `skeleton_core` through the outbound helper, with the core address from an environment variable, a timeout and an explicit error response; never a retry that hides the failure) and `services/skeleton_edge/Dockerfile` under the same rules as T197. Makes T186 and T187 pass together with T197.
- [ ] T199 [P] [US6] Create `services/skeleton_edge/{slo.md,runbook.md,warm_start.md}`: SLO placeholder with indicator, objective written as `to be set by the owning feature`, owner feature and status `placeholder`; runbook stub with symptoms, first checks, escalation, rollback; warm-start statement `holds in-memory state: no`.
- [ ] T200 [P] [US6] Create `services/skeleton_core/{slo.md,runbook.md,warm_start.md}` under the same rules as T199.
- [ ] T201 [P] [US6] Implement `tools/repo_checks/service_docs.py` and register it in `tools/repo_checks/__main__.py`. Makes T188 pass.
- [ ] T202 [P] [US6] Implement `tools/prompt_lock/{lock.py,__main__.py}` (subcommands `check` and `update`) on top of `src/eios/llm_gateway/prompt_lock.py` from T122. Usage: `uv run python -m tools.prompt_lock check`. Makes T189 and T190 pass. Add the module to the tooling register in `docs/conventions.md`.
- [ ] T203 [US6] Append gate row `prompt_lock` (stage `pr`, command `uv run python -m tools.prompt_lock check`) to `config/gates.yaml` with fixture `tests/fixtures/faulty_changes/prompt_lock/` (a prompt file edited without a new version). T030 then covers it with no code change.
- [ ] T204 [US6] Append gate row `service_docs` (stage `pr`, command `uv run python -m tools.repo_checks service-docs`) with fixture `tests/fixtures/faulty_changes/service_docs/` (a service directory missing `runbook.md`).
- [ ] T205 [P] [US6] Create `config/cost_linkage.yaml`: the staleness threshold (set at implementation and tagged `[TARGET]`) and the map from each gateway configuration's model price keys to driver names. Format fixed by T183.
- [ ] T206 [P] [US6] Create `docs/cost_model.csv` with one row per cost driver the platform will incur: model tokens (price source names spike S-01 and the row is tagged `[SPIKE]`), compute, container registry storage, object storage, document-store operations, key management, logging and tracing, scanning, and CI minutes. Quantities and prices stay blank unless a verified source and date exist; no price is invented, and every row has a tag and `reconciliation` set to `pending`. Makes the real-file half of T193 pass.
- [ ] T207 [US6] Implement `tools/cost_check/{rules.py,linkage.py,totals.py,__main__.py}`: all contract rules, the T179 additions, totals over verified rows only, report with source, date and tag for every figure, exit-code contract. Makes T181, T182 and T183 pass.
- [ ] T208 [US6] Append gate row `cost_check` (stage `pr`, command `uv run python -m tools.cost_check`) with fixture `tests/fixtures/faulty_changes/cost_check/` (a row with a price and no source).
- [ ] T209 [P] [US6] Create `config/budgets.yaml`: the threshold list (50, 80, 100 `[TARGET]`) and, per environment, a budget amount tagged `[ASSUMPTION]`. The implementer sets each amount when the account exists and records the reasoning; this task prescribes no value.
- [ ] T210 [P] [US6] Create `infra/modules/budget_alerts/`: a budget resource with thresholds and amount as required variables with no defaults, a notification channel resource, outputs for the channel identifier.
- [ ] T211 [US6] Wire `budget_alerts` into `infra/envs/dev/`, `infra/envs/stage/` and `infra/envs/prod-like/` (T085), reading thresholds and amounts with `yamldecode(file(...))` from `config/budgets.yaml` so no number is duplicated in Terraform.
- [ ] T212 [US6] Extend `tools/infra_checks/policy.py` (T071) with the budget rule set and a `--rules budget` option. Makes T191 pass.
- [ ] T213 [US6] Append gate row `budget_alerts` (stage `pr`, command `uv run python -m tools.infra_checks --rules budget`) with fixture `tests/fixtures/faulty_changes/budget_alerts/` (an environment composition missing one threshold).
- [ ] T214 [P] [US6] Implement `tools/budget_probe/{payload.py,__main__.py}`: usage `uv run python -m tools.budget_probe --env dev --threshold 80 [--dry-run]`; dev only; publisher injected. Makes T192 pass.
- [ ] T215 [P] [US6] Create `docs/runbooks/budget-alert-test.md`: how to trigger one threshold in `dev`, what the alert looks like, how to confirm delivery, how to clean up.
- [ ] T216 [US6] Extend the container scan gate (T050) so it builds and scans each `services/*/Dockerfile`. The existing overlay stays; add an image with a known-vulnerable base to a second overlay only if the scanner supports a local fixture.
- [ ] T217 [US6] Run T179 to T193 until green, and run T030 to confirm the gates added here (`prompt_lock`, `service_docs`, `cost_check`, `budget_alerts`) each fail on their overlay and pass on the clean skeleton.
- [ ] T218 [US6] Execute quickstart scenario 9 (SC-010): one request through both services showing the shared identifier in traces and logs; `cost_check` output; the three thresholds in each environment's plan; one threshold triggered in `dev`. Record in `docs/evidence/sc-010-observability-cost.md`. If the `dev` account is not available, record the trigger step as not executed with the reason, never as passed.

**Checkpoint**: a request is traceable end to end, prompts are versioned and drift-checked, cost figures are sourced and dated, and spend alerts exist before any workload does.

---

## Phase 9: Polish and Cross-Cutting Concerns

**Purpose**: close the loop between design documents and the built platform, prove the whole thing together, and hand it over. No story label.

- [X] T219 Verify `docs/runbooks/` holds a procedure for every operational case the spec names: rollback (FR-010), rotate-and-purge of a committed secret, the pipeline-unavailable emergency path with retroactive review, gate quarantine with owner and expiry, and the budget alert test (T215). Create only the missing ones; each states trigger, steps, owner and how the incident is recorded.
- [X] T220 Replace the placeholder entry-point names in `specs/001-platform-foundations/quickstart.md` (for example `<local-check>`) with the real commands documented in `docs/conventions.md` and the `Makefile`. Change nothing else in the guide.
- [X] T221 Record plan deviations. Update `specs/001-platform-foundations/plan.md` (project structure) and `data-model.md` where the built layout differs from the design, listing each addition with the task that introduced it (see Notes below for the known set). This fills the deviations section that T005 reserves in `docs/conventions.md`.
- [X] T222 Update `CLAUDE.md` at the repository root: replace the statement that no build, test or lint commands exist with the real ones (setup, check, test, lint, types, each gate tool), keeping every other section as it is.
- [X] T223 Run the full suite with coverage: `uv run pytest` with the 80% `[TARGET]` coverage gate, the linter and the type checker. Add missing tests for any module under the threshold; do not lower the gate.
- [X] T224 Run the local check entry point on the real repository. Every gate in `config/gates.yaml` passes and a Pipeline Run Record is written under `evals/reports/`; fix findings at the source, never by loosening a gate.
- [X] T225 Review all F00 code with the code-reviewer agent; address every CRITICAL and HIGH finding and record the disposition of the rest in `docs/evidence/code-review.md`.
- [X] T226 Review secrets handling, identities, the gateway, the skeleton services and the promotion path with the security-reviewer agent; fix CRITICAL and HIGH findings first, then record the outcome in `docs/evidence/security-review.md`.
- [X] T227 Execute quickstart scenarios 1 to 9 in order after T223 to T226, and create `docs/evidence/README.md` mapping SC-001 to SC-011 to the evidence file and Pipeline Run Record for each. Scenarios needing a cloud account that is not available are listed as not executed with the reason.
- [X] T228 Set F00 `complete: true` in `docs/feature_register.yaml` only when T227 shows every success criterion with evidence, then run `uv run python -m tools.readiness F00` and `uv run python -m tools.adr_check` once more.

---

## Dependencies & Execution Order

### Phase dependencies

| Phase | Tasks | Depends on | Blocks |
|---|---|---|---|
| 1 Setup | T001 to T008 | none | everything |
| 2 Foundational | T009 to T022 | Setup | every story |
| 3 US1 gates (P1) | T023 to T057 | Foundational | every other story (gate runner, `config/gates.yaml`, `tests/fixtures/clean_skeleton/`) |
| 4 US2 environments (P1) | T058 to T100 | US1 | US6 (T082, T083, T085) |
| 5 US3 gateway (P1) | T101 to T131 | US1 | US5 (open-decision engine T126, T127), US6 (T122, trace, redaction) |
| 6 US4 labels (P2) | T132 to T153 | US1 | none |
| 7 US5 decisions (P2) | T154 to T178 | US1, US3 | none |
| 8 US6 observability and cost (P3) | T179 to T218 | US1, US2, US3, US4 | Polish |
| 9 Polish | T219 to T228 | all stories wanted in this release | none |

### Within a story

- Contract amendment tasks first, where a story has one (T154, T179).
- Tests before implementation. Every test task is RED when written and its implementation task names the test it turns green.
- Fixtures and test support before the tests that use them.
- Pure libraries before the tools that use them, tools before their gate rows, gate rows before the story's closing run of T030.
- The closing evidence task of each story is last and records only observed results.

### Cross-story coupling to watch

- `config/gates.yaml` is appended by US1 (T050 and the first gates), US2 (T095), US3 (T129), US4 (T150), US5 (T176), US6 (T203, T204, T208, T213). Rows are appended, never reordered; concurrent branches must rebase on this file.
- `config/open_decisions.yaml`: US3 fixes the structure (T127), US5 extends it (T168). Do not restructure it in US5.
- T141 checks structured config tags against `config/llm_gateway.*.yaml` (US3) and the cost model; its cost-model half uses fixtures, and the real file is checked by T193.
- T174 creates `docs/feature_register.yaml` with F00 incomplete; only T228 flips it.

### User story independence

- US1 is the only story that unlocks all others. After US1, US2, US3 and US4 can proceed in parallel; US5 follows US3; US6 follows US2, US3 and US4.
- Each story's independent test (listed at the head of its phase) can be run without the stories that depend on it.

---

## Parallel Examples

Tasks marked `[P]` touch different files and have no unmet dependency; run them together within the groups below.

- **Foundational**: T010, T011, T012, T013, T014, T015 (tests), then T016 to T021 (implementations).
- **US1**: the test tasks T024 to T031 together; fixtures T032 and its siblings together; tool wrappers for lint, types, coverage and secret scan together once T050 has chosen the tools.
- **US2**: T058, T059, T060 and T068 (infra test files) together; Terraform modules T081 to T084 together; identities T086 alongside; T085 after the modules.
- **US3**: T103 to T109 (contract tests) together; `caps.py`, `replay_cache.py`, `trace.py`, `prompt_lock.py` (T119 to T122 area) together; T126 and T127 before any US5 work.
- **US4**: T132 to T142 test files together; T143, T144 config files together; T145, T146, T147 rule modules together; T148 after them.
- **US5**: T155 to T163 test files together; T164, T165, T166 together; ADR backfills T169 to T172 and spike records T173 together; T175 after them.
- **US6**: T180 to T193 test files together; T195, T196, T197, T198, T199, T200, T201, T202, T205, T206, T209, T210, T214, T215 together; T207, T211, T212 after their inputs.

Example launch for US6 tests:

```text
Agent A: T181, T182, T183   tests/unit/tools/cost_check/
Agent B: T184, T185         tests/unit/common/
Agent C: T186, T187         tests/contract/services/, tests/integration/
Agent D: T188, T189, T190   service docs and prompt lock tests
Agent E: T191, T192         budget and probe tests
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 Setup, then Phase 2 Foundational (T001 to T022). Stop and confirm the gate in T022.
2. Phase 3 US1 (T023 to T057): blocking gates on the pipeline, hook registry for later features, local check.
3. **Stop and validate**: quickstart scenarios 1 and 2. A faulty change cannot merge and a clean one can. This alone is a demonstrable engagement artefact: an evidence-gated delivery pipeline.

### Incremental delivery

1. P1 complete: add US2 (environments, identity, secrets) and US3 (gateway) in parallel; validate scenarios 3, 4, 5.
2. P2: add US4 (labels) and US5 (decisions); validate scenarios 6 and 7. US4 also lets the gates police the documents the later phases produce.
3. P3: add US6 (observability and cost); validate scenario 9.
4. Polish: T219 to T228, then scenario 8 (rollback) is rehearsed on `stage` before any `prod-like` promotion, as the spec requires.

### Parallel team strategy

After US1: one track on US2 (infrastructure), one on US3 then US5 (gateway then decisions), one on US4 (labels). US6 starts when US2, US3 and US4 are merged.

### Rules that hold throughout

- A task is done only when its test is green and, if it adds a gate, T030 covers it.
- No gate is loosened to make a run pass; a flaky gate is quarantined with an owner and expiry.
- Evidence tasks record what was observed. A step that could not run is recorded as not executed.
- No model, price, brand or version is hardcoded; versions are `[SPIKE]` until verified.
- Nothing here chooses an outcome for ADR-002, 003, 009 or 014.

---

## Notes

### Contract inconsistencies resolved in these tasks

- Cap with a cached result: the gateway contract could be read as `cap_reached` or `replay`; the spec's edge case allows cached replays after the cap, so T101 amends the contract to `replay`.
- Proposed ADR with no file: `decision-and-spike-records.md` can be read to require a file for every index row; `data-model.md` and `research.md` do not. T154 aligns the contract: only `Accepted` and `Superseded` require a file.
- ADR evidence wording: backfilled records cite design documents rather than experiments; T154 allows that and the record says why.
- Spike fields: the source and the contract list slightly different field sets; the template uses their union (T164).
- Cost model: the contract has no place for bill reconciliation and no rule against hand-typed totals; T179 adds both.

### Planned deviations from `plan.md` (to be folded back in T221)

- Extra common modules: `src/eios/common/secret_reader.py` and others introduced by Foundational and US2.
- Extra tool packages: `tools/records/`, `tools/common/`, `tools/infra_checks/`, `tools/prompt_lock/`, `tools/budget_probe/`.
- Extra configuration files: `config/repo_checks.yaml`, `config/gates.yaml`, `config/quarantine.yaml`, `config/rollback.yaml`, `config/cost_linkage.yaml`, `config/budgets.yaml`, `config/risk_exceptions.yaml`, `config/label_allowlist.yaml`.
- Extra infrastructure and data files: `infra/identities.yaml`, the KMS key ring inside `secret_store`, `docs/feature_register.yaml`, `docker-compose.dev.yml`.
- Extra supporting trees: `tests/support/`, `schemas/` (byte-identical copies of the contract schemas), `docs/evidence/`, `specs/<feature>/dependencies.yaml`.

### Labels in this file

Figures in this document follow the labelling regime: 50%, 80%, 100% budget thresholds and the 80% coverage gate are `[TARGET]`; tool and library choices are `[ASSUMPTION]` with versions `[SPIKE]`. Task IDs, phase numbers and ranges are identifiers, not claims.

### What comes next

`/speckit-analyze` should check this file against the specification (every FR and SC has a task and a test) before `/speckit-implement`.




