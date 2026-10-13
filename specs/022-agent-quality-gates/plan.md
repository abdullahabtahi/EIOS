# Implementation Plan: Agent Quality Gates

**Branch**: `spec/022-agent-quality-gates` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/022-agent-quality-gates/spec.md`. Design context: `docs/agent-architecture.md`, `docs/adk-research.md`, `docs/lighthouse.md`.

## Summary

Build the yardstick before the rebuild. A runtime-neutral **Turn Record** captures every evaluated turn; a small set of **deterministic checkers** (faithfulness, trajectory, safety) judge a record with no model call; golden and attack **cases** drive an **Agent Port** so the same suites run against today's copilot, the future ADK runtime and a trivial stand-in; a **baseline report** on today's copilot runs red on purpose; **telemetry** derives from the same record. The checkers are plain standard-library Python so they run both in our CI and, unchanged, as native `agents-cli eval` metrics (spike S-EVAL-1). Suites register as rows in the existing `evals/registry.yaml`, extending spec 005's harness instead of adding a second one.

## Technical Context

**Language/Version**: Python 3.14 for the package. The checker core (`eios/agent_gates/core/`) is standard-library only and must import under Python 3.12, because `agents-cli` executes metric files in its own 3.12 process (RUN: the CLI path is `python3.12`).

**Primary Dependencies**: none new at runtime (pydantic, PyYAML already present). `agents-cli` 1.10.0 is an optional adapter tool, not a dependency.

**Storage**: files. Turn Records as JSON Lines under `evals/recorded/`; reports as JSON and Markdown under `evals/reports/`; telemetry sink is a local JSONL writer. The BigQuery table for telemetry is a contract (schema file) only; its writer is the ADK analytics plugin in spec 021.

**Testing**: pytest, test-first. Three layers: (1) checker unit and mutation tests on every PR; (2) re-judging of a committed corpus of recorded records on every PR; (3) live runs through the existing LLM gateway, scheduled and on release candidates under a spend cap.

**Target Platform**: CI (existing `pr.yml`, `make check`) and local development.

**Project Type**: library plus suites inside the existing `EIOS/` Python project; no new service.

**Performance Goals**: re-judge 200 recorded turns under 2 minutes (SC-003 `[ASSUMPTION]`); deterministic PR gates under 10 minutes (SC-009 `[TARGET]`).

**Constraints**: no live model on pull requests (FR-023); ADR-002 (no vendor SDK imports or model ids in new code; live runs reach the model only through `llm_gateway`); files at most 400 lines typical, 800 hard; frozen models; metric core imports nothing from `eios`.

**Scale/Scope**: about 56 golden cases (AML 20, partner 12, executive 12, compliance 6, operations 6) `[ASSUMPTION]`, at least 15 attack cases (3 per family), the 13 pinned figure cases, and a generated mutation corpus.

## Constitution Check

*GATE: pass before Phase 0; re-checked after Phase 1.*

| Principle or constraint | Status | How the plan satisfies it |
|---|---|---|
| I. LLMs never compute metrics | Pass | The faithfulness checker is the executable form of this principle; no LLM judge gates (FR-017) |
| II. No autonomous write-back | Pass | A safety case asserts no agent toolset contains `approve_action` or `execute_action`; attack suite covers stage-then-self-approve |
| III. Honest uncertainty | Pass | Trajectory suite requires "insufficient data" when a tool or data is missing |
| IV. Ontology-only access | Pass | Cases name capabilities, not tables; ground truth stays in the eval-only store |
| V. Provenance labelling | Pass | Every threshold and count in the plan carries `[ASSUMPTION]` or `[TARGET]`; report separates measured from assumed |
| VI. Eval-first, baselines, anti-circularity (non-negotiable) | Pass | This feature is the baseline; dev, validation and sealed splits per ADR-015; sealed only on release candidates; ground truth never in agent context (FR-012) |
| VII. Specialised agents, decoupled pipelines | Neutral | Suites are per workstation |
| VIII. Deterministic fallback and operability | Pass | Replay fallback is a recorded field and a checked behaviour; inconclusive never passes (FR-024) |
| Provider neutrality (ADR-002) | Pass | Live runs through `llm_gateway`; the `agents-cli` shim contains no SDK import or model id |
| Immutability, file size, validation at boundaries | Pass | Frozen pydantic records; schema validation on every loaded case and record |
| Open decisions stay open | Pass | The plan assumes no ADK, MCP Toolbox or storage product |

Post-design re-check: pass (see Complexity Tracking for the one deliberate duplication).

## Project Structure

### Documentation (this feature)

```text
specs/022-agent-quality-gates/
├── spec.md
├── plan.md                 # this file
├── research.md             # decisions and spike evidence
├── data-model.md           # entities and validation rules
├── quickstart.md           # runnable validation scenarios
├── contracts/
│   ├── agent-port.md
│   ├── turn-record.schema.json
│   ├── telemetry-event.schema.json
│   ├── golden-case.md
│   └── agents-cli-trace-mapping.md
├── checklists/requirements.md
└── tasks.md                # next step (/speckit-tasks)
```

### Source Code (repository: `EIOS/`)

```text
src/eios/agent_gates/
├── core/                    # stdlib only, imports nothing from eios, parses under Python 3.12
│   ├── figures.py           # extract, normalise (scale, unit, spelled-out numbers)
│   ├── facts.py             # flatten tool results to typed facts with label tokens
│   ├── exempt.py            # the one reviewed list of exempt categories
│   ├── faithfulness.py      # judge(record) -> figure verdicts
│   ├── trajectory.py        # judge(record, case) -> verdict
│   ├── safety.py            # judge(record, attack) -> verdict
│   └── consistency.py       # judge(record, workstation payload) -> disagreements (FR-026)
├── records.py               # frozen pydantic TurnRecord and friends; to and from JSON
├── port.py                  # AgentPort protocol, TurnRequest, ToolFixture
├── adapters/
│   ├── copilot.py           # today's CopilotEngine, tool calls captured by spying on its dispatcher
│   └── standin.py           # trivial agents for the parity story and tests
├── cases.py                 # golden and attack case models, loaders, split handling
├── capabilities.py          # capability ids and the per-runtime tool name map
├── telemetry.py             # TurnRecord -> TelemetryEvent, redaction, scanner, JSONL sink
└── report.py                # baseline and release report (JSON, Markdown, one page)

src/eios/cockpit/server.py   # one added call in `query_copilot` that emits a telemetry event (FR-020)

evals/
├── agent/
│   ├── faithfulness_suite.py  trajectory_suite.py  safety_suite.py  baseline.py
│   ├── metrics/               # thin files for `agents-cli eval grade` (custom_function_file)
│   └── eval_config.yaml
├── golden/agent_cases/        # YAML per workstation (extends the dialogue format)
├── golden/attacks/            # YAML attack cases, paraphrased to avoid blocklist keywords
├── recorded/                  # committed Turn Record corpus (good and known-bad)
├── agent/screen_payloads.py   # loads workstation payloads from the contract the cockpit serves
└── registry.yaml              # new rows only (FR-025)

tests/agent_gates/             # unit, mutation, corpus re-judge, parity, telemetry scan
docs/lighthouse-study-protocol.md   # M1/M2 timed-study protocol (FR-019)
```

**Structure Decision**: one new package `eios.agent_gates` plus suites under the existing `evals/` tree. The `core/` split exists only because the Google eval CLI runs metric files in a different interpreter than our package (see Complexity Tracking).

## Implementation phases (order of work; tasks come next)

0. **Faithfulness core, test-first.** Start red with the 13 pinned cases, then the mutation corpus (scale, wrong-field and unit swaps applied to faithful answers) and templated faithful paraphrases. Calibrate until all mutations are caught and no faithful paraphrase is blocked. This is the riskiest piece (FR-005) and goes first.
1. **Turn Record, Agent Port, copilot adapter, recorder.** Capture today's copilot turns (tool name, arguments, result) by spying on `run_omcp_tool`; record identity source, replay flag, audit verdict, latency.
2. **Safety and adversarial suites.** Red lines RL-1 to RL-7 as behavioural checks; five attack families, paraphrased; tool-result injection through `ToolFixture`; canary tokens for exfiltration; all-repeats-pass rule.
3. **Capabilities, golden cases and screen consistency.** Introduce capability ids; add the agent-versus-workstation check (FR-026); re-anchor the ten existing dialogues (which name tools that exist nowhere) and add the missing workstations; trajectory suite.
4. **Baseline report and study protocol.** Live run of the dev split on today's copilot under a spend cap; one-page report; red results listed with evidence.
5. **Telemetry.** Event schema, redaction, scanner, local sink.
6. **Parity.** Stand-in agent fails the right suites; `agents-cli eval grade` adapter proven on the recorded corpus.

## Complexity Tracking

| Deviation | Why needed | Simpler alternative rejected because |
|---|---|---|
| The checker core is stdlib-only and duplicated by thin metric shim files | `agents-cli` runs metric files in its own Python 3.12 process, which cannot import our 3.14 package (RUN, S-EVAL-1) | Making the CLI path the only path would couple our CI to a tool we do not control; making our runner the only path would forgo Google's native eval reports and the future `eval generate` against the ADK runtime |
| Capability ids between cases and tool names | Tools are about to change (spec 023); cases must not rot | Naming today's tools in cases would force a rewrite of every case at 023 |
