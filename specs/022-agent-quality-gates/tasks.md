# Tasks: Agent Quality Gates

**Input**: Design documents in `specs/022-agent-quality-gates/` (spec, plan, research, data-model, contracts, quickstart)

**Prerequisites**: plan.md, spec.md (done). Paths are relative to `EIOS/` unless they start with `docs/` or `specs/`.

**Tests**: Included and written first. Constitution Principle VI makes test-first (red, green, refactor) and 80% coverage on unit-testable code mandatory. Every "Tests" task must be seen failing before its implementation task starts.

**Organization**: By user story, in priority order. US1 and US2 are P1, US3 and US4 are P2, US5 and US6 are P3.

## Format: `- [ ] T### [P?] [US#?] Description with file path`

- **[P]**: parallelisable (different files, no dependency on an unfinished task)
- **[US#]**: user story from spec.md (story phases only)

---

## Phase 1: Setup

- [ ] T001 Create the package skeleton `src/eios/agent_gates/__init__.py`, `src/eios/agent_gates/core/__init__.py` and `src/eios/agent_gates/adapters/__init__.py`; keep `core/__init__.py` free of any import from `eios`
- [ ] T002 [P] Create `tests/agent_gates/__init__.py` and a `conftest.py` with a fixture that loads recorded Turn Records from `evals/recorded/`
- [ ] T003 [P] Create `evals/agent/__init__.py`, `evals/agent/metrics/` and `evals/golden/agent_cases/` and `evals/golden/attacks/` directories (each with a `.gitkeep` until populated)
- [ ] T004 [P] Add a guard test `tests/agent_gates/test_core_isolation.py`: every module under `src/eios/agent_gates/core/` imports only the standard library (AST scan) and parses under Python 3.12 (`uv run --python 3.12 python -c "import ast, sys; ast.parse(open(sys.argv[1]).read())"`); expected to pass vacuously now and guard every later task

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the shared record, port, capability map and case loaders.

- [ ] T005 [P] Contract tests for Turn Record in `tests/agent_gates/test_records.py`: valid record accepted; replay without reason, inconclusive without reason, a call with both result and error, unknown role and extra fields rejected, using `specs/022-agent-quality-gates/contracts/turn-record.schema.json`; JSON round trip equality
- [ ] T006 Implement frozen `TurnRecord`, `ToolCall`, `Binding` and JSON (de)serialisation in `src/eios/agent_gates/records.py` (depends on T005)
- [ ] T007 [P] Tests for verdict and gate models in `tests/agent_gates/test_verdicts.py`: `inconclusive` never yields `proven`; counts per verdict; first failing case carries its evidence
- [ ] T008 Implement `Verdict`, `FigureVerdict`, `GateResult` in `src/eios/agent_gates/verdicts.py` (depends on T007)
- [ ] T009 [P] Tests for capabilities in `tests/agent_gates/test_capabilities.py`: lookup by runtime, `unavailable` yields `capability_missing`, no mapping may expose `approve_action` or `execute_action` for any agent role
- [ ] T010 Implement capability ids and the per-runtime map in `src/eios/agent_gates/capabilities.py` and `src/eios/agent_gates/capability_map.yaml`; map the copilot's six tools (`get_governed_metric`, `inspect_aml_entity`, `query_graph_topology`, `inspect_partner_churn`, `run_causal_what_if`, `stage_action_intent`) and mark its two retrieval tools as fixture-only (depends on T009)
- [ ] T011 [P] Tests for case loading in `tests/agent_gates/test_cases.py`: golden case and attack case validation per `contracts/golden-case.md`; invalid file fails the suite; a ground-truth key in an agent-visible field is rejected; split handling
- [ ] T012 Implement golden and attack case models and loaders in `src/eios/agent_gates/cases.py`, extending `GoldenDialogueScenario` from `src/eios/evals/models.py` without breaking the existing `dialogue-evals` suite (depends on T011)
- [ ] T013 [P] Implement `AgentPort`, `TurnRequest`, `ToolFixture` in `src/eios/agent_gates/port.py` per `contracts/agent-port.md`, with a test in `tests/agent_gates/test_port.py` that a deadline overrun yields an `inconclusive` record, not an exception

**Checkpoint**: records, port, capabilities and case loaders exist; stories can proceed.

---

## Phase 3: User Story 1 - No unsupported figure ships (P1) 🎯 MVP

**Goal**: a deterministic faithfulness gate that classifies every figure in an answer and blocks a release on any unsupported figure.

**Independent Test**: the 13 pinned cases classify correctly (5 blocked, 8 accepted) and judging a stored run twice gives identical verdicts with no model call.

### Tests for User Story 1 (write first, see them fail)

- [ ] T014 [P] [US1] Pinned cases in `tests/agent_gates/test_faithfulness_pinned.py`: port the 13 cases from `tests/conversation/test_auditor_known_gaps.py` (6 survivors, 5 wrong figures, 2 faithful answers) as Turn Records in `evals/recorded/pinned/` using the same fixture tool results; assert expected verdicts
- [ ] T015 [P] [US1] Extraction and normalisation tests in `tests/agent_gates/test_figures.py`: thousands separators, currency symbols, `k`, `million`, `billion`, percentages, basis points (`1.2 bps` is not billions), multipliers (`16x`), spelled-out numbers up to the billions, rounding to the stated precision (`about 3.8 million` matches 3,820,000; `3.9 million` does not)
- [ ] T016 [P] [US1] Fact flattening tests in `tests/agent_gates/test_facts.py`: nested results, lists, unit family inference from sibling `unit` fields and name suffixes (`_usd`, `_pct`, `_bps`), label tokens from the path, per-case aliases
- [ ] T017 [P] [US1] Exempt-category tests in `tests/agent_gates/test_exempt.py`: port the cases from `tests/conversation/test_auditor_temporal_exemptions.py` (dates, timestamps, `v`-prefixed versions, `version 1.2.3`, statutory citations such as `31 CFR 1020.320`, `Form 111`, `FATF Recommendation 20`, identifier codes, list numbering; a bare decimal is not a version)
- [ ] T018 [P] [US1] Mutation tests in `tests/agent_gates/test_faithfulness_mutation.py`: generate mutants of faithful answers (scale times 100 and divided by 100, field swap, unit swap, dropped decimal, derived figure) and assert every mutant is caught; generate templated faithful paraphrases and assert none is blocked
- [ ] T019 [P] [US1] Structured-mode tests in `tests/agent_gates/test_faithfulness_bindings.py`: a record with explicit bindings is verified by value and unit equality; a binding that points at the wrong field fails

### Implementation for User Story 1

- [ ] T020 [P] [US1] Implement figure extraction and normalisation in `src/eios/agent_gates/core/figures.py` (standard library only; Python 3.12 parseable)
- [ ] T021 [P] [US1] Implement fact flattening in `src/eios/agent_gates/core/facts.py`
- [ ] T022 [P] [US1] Port the exempt categories from `src/eios/conversation/auditor_bridge.py` (statutory citation, timestamp and version patterns, identifier rule) into the single reviewed list `src/eios/agent_gates/core/exempt.py`
- [ ] T023 [US1] Implement `judge(record, aliases)` in `src/eios/agent_gates/core/faithfulness.py` per research R-2: value, unit family and label match; `wrong_field`, `ambiguous`, `derived`; conservative on ambiguity; structured mode when bindings exist; document the algorithm in the module docstring (depends on T020, T021, T022)
- [ ] T024 [US1] Calibrate against T014, T018 and T019 until all pass; record precision and recall on the mutation and paraphrase corpora in `specs/022-agent-quality-gates/research.md` under R-2 `[MEASURED]`
- [ ] T025 [P] [US1] Build the recorded corpus in `evals/recorded/faithfulness/`: the 13 pinned plus at least 187 further records (good and known-bad, across the five workstations) so the 200-turn speed test is real
- [ ] T026 [US1] Implement the suite in `evals/agent/faithfulness_suite.py` (`--records`, `--twice`, report to `evals/reports/agent_faithfulness.json`), failing the run on any unsupported figure
- [ ] T027 [US1] Register `agent-faithfulness` (tier `eval_smoke`) in `evals/registry.yaml`
- [ ] T028 [US1] Add `tests/agent_gates/test_rejudge_speed_and_determinism.py`: 200 recorded turns judged twice, verdicts identical, no network, under 2 minutes `[ASSUMPTION]` (SC-002, SC-003)

**Checkpoint**: US1 is a working release gate with no other story built. **This is the MVP.**

---

## Phase 4: User Story 2 - The agent cannot be talked into unsafe behaviour (P1)

**Goal**: red lines and attack families run against the agent from outside, and any successful attack is reported.

**Independent Test**: the safety suite runs against today's copilot and reports pass or fail per red line and per attack family, with paraphrased attacks reported separately.

### Tests for User Story 2 (write first)

- [ ] T029 [P] [US2] Judge tests in `tests/agent_gates/test_safety_judge.py`: `must_not` forms (`call:`, canary present, identity changed, `propose_after_injection`) evaluated on scripted Turn Records; a repeat that fails fails the case
- [ ] T030 [P] [US2] Toolset exclusion test in `tests/agent_gates/test_toolset_exclusion.py`: no agent role's toolset contains `approve_action` or `execute_action` (RL-2), checked over `capability_map.yaml` and over the copilot's declared tools
- [ ] T031 [P] [US2] Red-line coverage test in `tests/agent_gates/test_redline_coverage.py`: every RL-1 to RL-7 appears in `evals/agent/redline_map.yaml` with at least one behavioural check (SC-004)
- [ ] T032 [P] [US2] Copilot adapter tests in `tests/agent_gates/test_copilot_adapter.py` (scripted, no model): tool calls captured with arguments and results by spying on `run_omcp_tool`; `ToolFixture` applied at that point; `identity_source = request_body`; replay flag and reason mapped; `data_origin = fixture`

### Implementation for User Story 2

- [ ] T033 [US2] Implement the copilot adapter in `src/eios/agent_gates/adapters/copilot.py` (depends on T013, T032)
- [ ] T034 [P] [US2] Implement `judge(record, attack)` in `src/eios/agent_gates/core/safety.py` (standard library only)
- [ ] T035 [P] [US2] Write the red-line map `evals/agent/redline_map.yaml` linking RL-1 to RL-7 to behavioural checks and existing suites under `evals/suites/redlines/`
- [ ] T036 [P] [US2] Write attack cases: `evals/golden/attacks/injection_via_tool_text.yaml`, `stage_then_self_approve.yaml`, `direct_write_attempt.yaml`, `identity_or_role_impersonation.yaml`, `cross_scope_request.yaml`, each with at least 3 paraphrased cases that avoid the blocklist substrings in `copilot_engine.process_query` and at least 1 keyword case for contrast, plus a canary in the cross-scope case
- [ ] T037 [US2] Implement `evals/agent/safety_suite.py` (`--runtime copilot`, `--records-out`, `--live` for model-dependent cases, deterministic re-judge otherwise)
- [ ] T038 [US2] Register `agent-safety` (tier `red_line`, deterministic re-judge) and `agent-safety-live` (tier `validation`, live, spend-capped) in `evals/registry.yaml`

**Checkpoint**: US2 reports red-line and attack results; US1 and US2 together satisfy the P1 scope.

---

## Phase 5: User Story 3 - Right tools, bounded effort, honest refusal (P2)

**Goal**: golden questions per workstation judged on capabilities used, rounds and refusal behaviour.

**Independent Test**: golden cases for one workstation run and compare recorded capabilities to expected ones.

### Tests for User Story 3 (write first)

- [ ] T039 [P] [US3] Trajectory judge tests in `tests/agent_gates/test_trajectory_judge.py`: expected capabilities in order with allowed extras, forbidden capability fails, rounds over `max_rounds` fail, `capability_missing` is reported not passed, refusal required yields refusal marker and no figures, missing data yields an honest refusal
- [ ] T040 [P] [US3] Re-anchoring test in `tests/agent_gates/test_golden_reanchor.py`: every capability named in every golden case exists in `capabilities.py`, and none names a tool (the old dialogues name tools that exist nowhere)

### Implementation for User Story 3

- [ ] T041 [P] [US3] Implement `judge(record, case_turn)` in `src/eios/agent_gates/core/trajectory.py` (standard library only)
- [ ] T042 [P] [US3] Re-anchor the ten dialogues in `evals/golden/dialogues/*.yaml` into capability-based cases under `evals/golden/agent_cases/` (leave the originals so the existing `dialogue-evals` suite keeps running); note the unmoored tool names in the new files' header
- [ ] T043 [P] [US3] Write AML investigator cases (20) in `evals/golden/agent_cases/aml_investigator/`: triage, dossier, network, timeline, withdrawal risk, regulation lookup, SAR draft, propose hold, unanswerable, ambiguous follow-up, multi-turn, tool failure
- [ ] T044 [P] [US3] Write partner manager cases (12) in `evals/golden/agent_cases/partner_manager/`: worklist, drivers, integrity, comms (untrusted text), propose action, unanswerable
- [ ] T045 [P] [US3] Write executive cases (12) in `evals/golden/agent_cases/executive/`: briefing, metric movement, forecast, what-if, causal versus correlation, unanswerable
- [ ] T046 [P] [US3] Write compliance auditor cases (6) in `evals/golden/agent_cases/compliance_auditor/` and data operations cases (6) in `evals/golden/agent_cases/data_operations/`
- [ ] T047 [US3] Implement `evals/agent/trajectory_suite.py` and register `agent-trajectory` (tier `eval_smoke`, scripted re-judge) and `agent-trajectory-live` (tier `validation`, live) in `evals/registry.yaml`

**Checkpoint**: US3 judges any runtime's tool use against capability-level expectations.

---

## Phase 6: User Story 4 - A measured starting point on today's copilot (P2)

**Goal**: one report showing where the current copilot stands, red results included.

**Independent Test**: run the baseline on the dev split and produce one report with M3, M5, trajectory, red-line and attack results per workstation.

### Tests for User Story 4 (write first)

- [ ] T048 [P] [US4] Report tests in `tests/agent_gates/test_report.py`: per-workstation rates computed from scripted records; failures listed with evidence; share of fixture turns and of request-body identity shown; `inconclusive` listed separately and marks the gate "not proven"; only measured values appear
- [ ] T049 [P] [US4] Baseline runner tests in `tests/agent_gates/test_baseline_runner.py`: spend cap stops a run before it starts; provider outage yields `inconclusive`; repeats recorded; dev split only unless explicitly overridden; sealed split refused outside release-candidate CI

### Implementation for User Story 4

- [ ] T050 [US4] Implement `src/eios/agent_gates/report.py` (JSON and one-page Markdown)
- [ ] T051 [US4] Implement `evals/agent/baseline.py` (`--runtime`, `--split`, `--repeats`, live calls only through `llm_gateway`, model id from configuration, cap from `EIOS_AGENT_EVAL_MAX_TURNS`) (depends on T033, T050)
- [ ] T052 [P] [US4] Write the timed-study protocol `docs/lighthouse-study-protocol.md` for M1 and M2: cases, participants, intervals, recording sheet, medians; do not execute
- [ ] T053 [US4] Run the baseline once against an EIOS project (quota project set; `global` endpoint) and commit the report as `docs/agent-baseline.md`, tagging measured values `[MEASURED]`; list red results, the keyword versus paraphrased attack split and capability coverage
- [ ] T054 [US4] Update `docs/lighthouse.md` (M3 and M5 baseline rows) and `docs/adk.md` (A2 status) with the measured numbers and the link to `docs/agent-baseline.md`

**Checkpoint**: the "before" picture exists. Spec 021 can now claim improvement.

---

## Phase 7: User Story 5 - Visibility of every turn (P3)

**Goal**: each turn leaves a complete, redacted record that supports M3 and M5.

**Independent Test**: run turns and inspect events: all fields, zero raw identifiers.

### Tests for User Story 5 (write first)

- [ ] T055 [P] [US5] Telemetry tests in `tests/agent_gates/test_telemetry.py`: event derived from a Turn Record has every required field and validates against `contracts/telemetry-event.schema.json`; raw identifiers rejected; excerpt bounded and redacted
- [ ] T056 [P] [US5] Scanner test in `tests/agent_gates/test_telemetry_scan.py`: a full suite run's events contain 0 raw identifiers (SC-008); a planted raw identifier is detected

### Implementation for User Story 5

- [ ] T057 [US5] Implement `src/eios/agent_gates/telemetry.py`: `TurnRecord` to `TelemetryEvent`, redaction, scanner, JSONL sink
- [ ] T058 [US5] Emit one event per live turn from `query_copilot` in `src/eios/cockpit/server.py` using the fields the route has (role, latency, replay flag and reason, audit status, citation count, tool trace count, session id); keep the change minimal and covered by a test in `tests/cockpit/test_copilot_telemetry.py`
- [ ] T059 [P] [US5] Add an M3 and M5 computation from events to `src/eios/agent_gates/report.py` and a test that both derive from events alone

**Checkpoint**: US5 provides the production-side data for the lighthouse metrics.

---

## Phase 8: User Story 6 - Any new runtime is judged by the same gates (P3)

**Goal**: the same case ids run unchanged against another runtime and, via Google's eval CLI, as native metrics.

**Independent Test**: suites run against the copilot and the `always42` stand-in; the stand-in fails the right suites; `agents-cli eval grade` reproduces the verdicts.

### Tests for User Story 6 (write first)

- [ ] T060 [P] [US6] Parity test `tests/agent_gates/test_parity.py`: same case ids against `copilot` (scripted) and `standin:always42`; the stand-in fails faithfulness and trajectory with the stated reasons
- [ ] T061 [P] [US6] Trace-mapping test `tests/agent_gates/test_agents_cli_mapping.py`: a Turn Record maps to an eval case with `prompt`, `responses` and `agent_data` per `contracts/agents-cli-trace-mapping.md`, and the `responses` field is always present

### Implementation for User Story 6

- [ ] T062 [P] [US6] Implement the stand-in adapters in `src/eios/agent_gates/adapters/standin.py` (`always42`, `scripted`)
- [ ] T063 [P] [US6] Implement `to_agents_cli_case(record)` in `src/eios/agent_gates/records.py`
- [ ] T064 [P] [US6] Write the metric shims `evals/agent/metrics/faithfulness.py`, `trajectory.py`, `safety.py` (each `def evaluate(instance)`, loading `core/` by path, never `import eios`) and `evals/agent/eval_config.yaml`
- [ ] T065 [US6] Add `tests/agent_gates/test_agents_cli_grade.py` (marked `requires_agents_cli`, skipped when the CLI is absent) that runs `agents-cli eval grade` on the recorded corpus and compares scores with our own suite

**Checkpoint**: all six stories work independently.

---

## Phase 9: Polish and cross-cutting

- [ ] T066 [P] Raise coverage on `src/eios/agent_gates/` to at least 80% and add missing edge-case tests (spelled-out numbers at the extremes, empty answers, results with no numerics)
- [ ] T067 [P] Run `make lint`, `make types` and `repo_checks` over `src/eios/agent_gates/` and `evals/agent/`; split any file above 400 lines; confirm frozen models everywhere
- [ ] T068 Run `make check` and confirm no new failures beyond the known quarantined and flaky ones (CLAUDE.md section 8)
- [ ] T069 [P] Draft a scheduled live-eval workflow `.github/workflows/agent-eval-live.yml` (cron plus manual dispatch, spend cap, disabled until you approve it, because it needs the CI identity and the cloud quota project)
- [ ] T070 Walk through `specs/022-agent-quality-gates/quickstart.md` end to end and tick each scenario
- [ ] T071 Update `CLAUDE.md` with the one-line entry for `evals/agent/` and the agent-gates command, trimming an equal amount elsewhere (keep the file lean)

---

## Dependencies and order

- Phase 1, then Phase 2, then stories. US1 depends only on Phase 2 (records, verdicts).
- US2 depends on Phase 2 and the adapter (T033). US3 depends on Phase 2, the capability map and case loaders. US4 depends on US1, US2 (adapter) and US3 for a complete report. US5 depends on records only. US6 depends on records, the port, and the suites it exercises.
- Recommended order: Phase 1, Phase 2, US1 (MVP, stop and review), US2, US3, US4, US5, US6, Polish.
- Within a story: tests, then core logic, then suites and registry rows. Registry rows (`evals/registry.yaml`) are the only shared file between stories; add them in the story that owns them to avoid conflicts.

## Parallel opportunities

- Phase 2: T005, T007, T009, T011, T013 are independent files.
- US1: tests T014 to T019 together; then T020, T021, T022 together.
- US2: T029 to T032 together; then T034, T035, T036 together.
- US3: T043 to T046 (case authoring) together after T041.
- US5 and US6 can proceed in parallel once Phase 2 is done.

## Implementation strategy

1. **MVP = Phase 1, Phase 2 and US1.** It delivers a usable release gate (M3) on its own. Stop there for review.
2. Add US2 next: the other P1 scope and the non-negotiable constitutional principle.
3. US3 and US4 together give the baseline; do not start spec 023 or 021 before T053.
4. US5 and US6 are P3 and can slip without blocking the baseline; US6's metric shims (T064) are needed before spec 021 can use `agents-cli eval generate`.
5. Commit on `spec/022-agent-quality-gates` after each checkpoint; one PR (#37) carries the feature.
