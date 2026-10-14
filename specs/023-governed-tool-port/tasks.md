# Tasks: Governed Tool Port

**Input**: [spec.md](spec.md), [plan.md](plan.md). Paths are relative to `EIOS/` unless they start with `docs/` or `specs/`.

**Tests first**: each "Tests" task is written and seen failing before the task after it. 80% coverage on new code.

## Format: `- [ ] T### [P?] [US#?] Description with file path`

---

## Phase 1: Setup

- [X] T001 Package skeleton `src/eios/ontology/omcp/port/__init__.py` and `tests/ontology/port/__init__.py`

## Phase 2: Foundation (blocks every story)

- [X] T002 Tests for contracts: `ToolResult` envelope rejects a figure with no unit, a missing as-of or origin; `ToolError` codes; error codes stay aligned with `agent_gates.records.ToolErrorCode` (`tests/ontology/port/test_contracts.py`)
- [X] T003 `src/eios/ontology/omcp/port/contracts.py`: `Marking`, `DataOrigin`, `ToolResult`, `ToolError`, `ToolErrorCode`, strict id types; extend `agent_gates/records.py` `ToolErrorCode` with `FORBIDDEN_ROLE` and `INVALID_ARGUMENTS`
- [X] T004 [P] Tests for `Principal` (`tests/ontology/port/test_principal.py`): uid from the verified operator, any verified operator may use any of the five workstations, an unknown workstation is refused, dev anonymous operator gets the dev principal, a role or id claimed in text or body cannot change the principal
- [X] T005 [P] `src/eios/ontology/omcp/port/principal.py` with the single `entitled_workstations` rule; no change to `cockpit/auth.py`
- [X] T006 [P] Tests for entities (`tests/ontology/port/test_entities.py`): the three partner aliases resolve to one canonical id, unknown id is `NOT_FOUND`, conflicting alias map fails validation, free text rejected
- [X] T007 [P] `src/eios/ontology/omcp/port/entities.py` (alias map as data in `src/eios/ontology/omcp/port/aliases.yaml`)
- [X] T008 Tests for the port core (`tests/ontology/port/test_port_core.py`): role allow-list, out-of-role refused and recorded, invalid arguments typed, output validated against its model, trace record, latency budget declared for every tool
- [X] T009 `src/eios/ontology/omcp/port/registry.py` (capability spec and decorator) and `service.py` (`GovernedToolPort`, `RefusalLog`)

## Phase 3: US1 AML slice (P1)

- [X] T010 [US1] Tests (`tests/ontology/port/test_aml_tools.py`): dossier fields and units, discrepancy 16.0 equals the workstation payload, unknown id `NOT_FOUND`, known-without-dossier `DATA_UNAVAILABLE`, alerts ranked, network flags hub suppression, timeline ordered, withdrawal risk, SAR draft sections reference facts
- [X] T011 [US1] `port/aml_tools.py`: `list_alerts`, `get_aml_dossier`, `get_network_evidence`, `get_activity_timeline`, `check_withdrawal_risk`, `draft_sar`
- [X] T012 [P] [US1] Add `aml:CR84920` to `evals/agent/screen_payloads.py` (read from `AMLWorkstationService`) and the case that uses it

## Phase 4: US2 Safe by construction (P1)

- [X] T013 [US2] Tests (`tests/ontology/port/test_safety.py`): for every role, no tool approves or executes (walk the registry); every out-of-role call is refused and recorded; the capability map roles equal the port roles; untrusted text is flagged, structured first, bounded; a marking the role lacks gives `FORBIDDEN_MARKING` and no restricted field
- [X] T014 [US2] Enforce markings per tool in `service.py`; `port/untrusted.py` wrapper

## Phase 5: US3 Partner slice (P2)

- [X] T015 [US3] Tests (`tests/ontology/port/test_partner_tools.py`): signals equal the radar payload for the golden partner (0.78, login decay), aliases resolve, no default partner, worklist ranked, integrity states observed facts only, comms untrusted, proposals carry label, cost, effect range, approver, no action constant
- [X] T016 [US3] `port/partner_tools.py`: `list_partner_worklist`, `get_partner_signals`, `get_partner_integrity`, `get_client_quality`, `read_partner_comms`
- [X] T017 [US3] `port/proposals.py`: `propose_hold`, `propose_partner_action`, closed action-kind enum with labels

## Phase 6: US4 Executive, compliance and operations (P2)

- [X] T018 [US4] Tests (`tests/ontology/port/test_executive_tools.py`): `compare_facts` difference, ratio, percentage with cited inputs and unit rules, mismatched units rejected; what-if attribution sums to 100.0, labelled simulation; causal label verified versus correlation only; metric returns unit and definition
- [X] T019 [US4] `port/shared_tools.py` (`get_metric`, `resolve_entity`, `get_causal_evidence`, `compare_facts`) and `port/executive_tools.py` (`get_briefing`, `get_forecast`, `run_what_if`)
- [X] T020 [P] [US4] Tests and `port/compliance_tools.py` + `port/ops_tools.py`: ledger timeline, intent status, audit status, verify chain; DQ board, reliability, drill status, calibration (`tests/ontology/port/test_compliance_ops_tools.py`)

## Phase 7: Judge through the agent port

- [X] T021 Tests (`tests/agent_gates/test_toolport_adapter.py`): the `toolport` runtime fills a record with identity source `verified_token`, only role-allowed calls, answers with result figures only
- [X] T022 `src/eios/agent_gates/adapters/toolport.py` and `--runtime toolport` in `evals/agent/baseline.py`
- [X] T023 Run `PYTHONPATH=src:. python -m evals.agent.baseline --runtime toolport` offline; record the result in `docs/agent-baseline.md` section 6 (before and after, same cases, thresholds unchanged); regrade saved runs with `--runtime recorded` where relevant
- [X] T024 Fix what the cases expose; cases that need specs 024 to 026 stay red and are reported as planned

## Phase 8: Server wiring

- [X] T025 Tests (`tests/cockpit/test_copilot_identity.py`): copilot endpoint takes identity from the verified operator, an unknown workstation is refused 422, `activeEntityId` and `context_entity_id` are both honoured
- [X] T026 `cockpit/server.py` `query_copilot`: `Depends(current_operator)`, principal built server side, both entity field names accepted

## Phase 9: Close

- [X] T027 `make check` green except the recorded pre-existing failures; mypy strict clean for `eios.ontology.omcp.port`
- [X] T028 Update this file, `docs/adk.md` status board (A3 prerequisite: port done), `docs/agent-architecture.md` section 2 (built names), memory; open one PR; merge when CI is green and the branch is current

## Outcome (2026-10-14)

Port: 28 capabilities, one entry point. Judged through the 022 port: 58 pass, 1 fail, 3 inconclusive against 33 pass and 28 fail for today's copilot (`docs/agent-baseline.md` section 6). The fail and the 3 inconclusive all need knowledge search (spec 024). Changes beyond the plan: the withdrawal scorer became a pure function (`score_withdrawal`) so a read never stages an intent; `RecordedRuntime` reads its runtime name from the records so any run can be re-graded; the baseline treats a planned capability as unserved, never as a pass; the AML golden case gained a screen payload; the copilot endpoint now refuses unknown workstations (it used to run every query as executive because the role comparison never matched). Known gaps: mypy still reports the recorded pre-existing errors elsewhere; the browser field rename and the entity reaching the engine ride with specs 021 and 030.

## Deferred (reasons in plan.md)

User Story 5 deprecation shims and retiring `conversation/tools.py` (spec 021), User Story 6 governance store separation (ADR-018 Proposed), knowledge capabilities (spec 024), `get_cohort_trend` (025), `get_market_context` (026), browser field rename (spec 030).
