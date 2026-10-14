# Implementation Plan: Governed Tool Port

**Branch**: `spec/023-governed-tool-port` | **Spec**: [spec.md](spec.md) | **Built 80/20**: a short plan, only the tasks the work needs.

## Summary

One typed catalogue of capabilities (`eios.ontology.omcp.port`) that sits in front of the workstation read models, so the assistant and the screen cannot disagree. A single `GovernedToolPort.call(principal, tool, args)` validates arguments, enforces the role allow-list from the verified principal, returns a typed envelope (value, unit, as-of, origin, source, marking) or a typed error, records every refusal, and never exposes approve or execute. The port is proven through the spec 022 agent port with a deterministic reference runtime (`toolport`), the golden cases and the attacks, not by hand.

## What this PR closes (measured in `docs/agent-baseline.md`)

| Measured gap | Closed by |
|---|---|
| 25 of 33 capabilities have no tool `[MEASURED]` | 28 typed capabilities (the other 5 are planned for specs 024 to 026, see Deferred) |
| Tools return constants for any id (0.84 vs 0.78 on the screen) | Handlers read the same services the workstation endpoints use; unknown id is `NOT_FOUND`, never a default |
| No role scoping, identity from the body `[MEASURED]` | `Principal` built from the verified operator; the port refuses out-of-role calls and records them |
| Approve and execute reachable in principle | Not registered in the catalogue; a test walks every role |
| What-if crashes on a missing p-value | `run_what_if` always returns a typed causal label (verified or correlation only) |

## Technical context

- Python 3.14, pydantic (`StrictModel` from `eios.common.validation`), pytest. No new dependency.
- Package: `src/eios/ontology/omcp/port/` (L2, the typed façade of the OMCP server, decision A-3). Files stay under 300 lines each.
- Source of truth for role toolsets is the port; `src/eios/agent_gates/capability_map.yaml` (eval side) must agree with it, enforced by a test, so the golden cases keep naming capabilities.
- All data is fixture today; every result says `data_origin = FIXTURE [ILLUSTRATIVE]` (data-strategy R1).

## Design

**Envelope.** Every successful result is a pydantic model that extends `ToolResult`: domain fields stay flat at the top level (the 022 judges address them by path, for example `discrepancy_multiplier`, `value`), plus `capability`, `entity_id`, `as_of`, `data_origin`, `source`, `marking`, `units` (path to unit for every figure) and `fact_ids` (path to a stable id `<capability>:<entity>:<path>`). A figure with no unit fails validation.

**Errors.** `ToolError(code, message, retryable)` with `NOT_FOUND`, `FORBIDDEN_ROLE`, `FORBIDDEN_MARKING`, `DATA_UNAVAILABLE`, `STALE`, `TIMEOUT`, `INVALID_ARGUMENTS`. Never an empty or default value. Free text is rejected where an id is required (ids match a strict pattern).

**Identity (B3).** `Principal(uid, workstation)`. `uid` comes from the verified `Operator` (`cockpit/auth.py`), never from the request. One rule covers everything (decided by the user): any verified operator may use any of the five workstations, and the workstation only selects which capabilities the assistant is offered. Firebase authority roles are not mapped to workstations. A question that claims a different role or operator id changes nothing. The rule lives in one function (`entitled_workstations`) so a real entitlement table can replace it later without touching callers.

**Port.** `GovernedToolPort(read_models, ledger)`: `list_tools(principal)` returns the role toolset; `call()` checks the allow-list, validates arguments against the tool's input model, dispatches, validates the output against its declared model, traces `(tool, role, duration, status)`, and appends refusals to a `RefusalLog`. A latency budget per tool is declared and checked in tests.

**Entities (FR-011).** `entities.py` holds the alias map as data (`PTR-882`, `P-882`, `AP-1029` resolve to the radar's canonical partner id) and validates it at import: two aliases resolving to different ids, or an alias that shadows a canonical id, fails the build.

**Read models (FR-010).** One module per domain wraps the existing services (`AMLWorkstationService`, `PartnerWorkstationService`, `ExecutiveCockpitService`, `ComplianceExplorerService`, `DataPlatformOperationsService`) and the existing engines (metric registry, scenario simulator). Where a service returns a constant for any id (the AML dossier today), the read model checks the id against the known set first and returns `NOT_FOUND` or `DATA_UNAVAILABLE`, so a constant can never pass for another entity.

**Untrusted text (FR-008).** `read_partner_comms` returns structured fields first and bounded excerpts last, each tagged `untrusted: true`, capped at 280 characters `[ASSUMPTION]`.

**Proposals (FR-013).** `propose_hold` and `propose_partner_action` return a `Proposal` (typed kind, operator-readable label, cost, expected effect with range, approver requirement) built from the workstation's retention deals; they stage nothing and sign nothing (RL-2). The action vocabulary is a closed enum owned by the intent hub side (decision recorded in memory: option A).

## Judging

`src/eios/agent_gates/adapters/toolport.py` is a deterministic reference runtime: it maps a question to capabilities with an explicit rule table limited to the caller's role, calls them through the real port with the verified identity, and answers only with figures from the results. It is not the agent (that is spec 021); it proves that the port makes every golden case answerable, makes every cross-scope attack impossible, and makes the answer agree with the screen. Run: `PYTHONPATH=src:. python -m evals.agent.baseline --runtime toolport`. The live model path is not used in this PR.

## Decisions (flag in the PR)

1. **One entitlement rule** (user decision): every verified operator may use every workstation. Known limit: the workstation is a client choice, so it scopes the assistant's tools but is not yet an authorization boundary between people. Revisit when real entitlements exist.
2. **Deprecation shims (FR-016) and retiring `conversation/tools.py` (FR-017)** are deferred to spec 021: the legacy copilot keeps working untouched until the ADK runtime replaces it, so the 24 conversation test files stay green and are ported then.
3. **Governance store separation (User Story 6)** is deferred: ADR-018 is still Proposed, and the work moves storage, not what the assistant can do.

## Deferred, with reasons

| Item | Reason |
|---|---|
| `knowledge.regulation`, `knowledge.policy`, `knowledge.sar_precedent` | Corpus and retrieval are spec 024; the cases that need them stay red and are reported as planned, not hidden |
| `exec.cohort_trend` | Needs the warm tier (spec 025) |
| `exec.market_context` | Needs reference products (spec 026) |
| User Story 5 shims, User Story 6 | See Decisions 2 and 3 |
| Browser field rename (FR-012, B2) | Frontend; server accepts both `context_entity_id` and `activeEntityId` now, the web change rides with spec 030 |

## Constitution check

I (no LLM-computed metrics): `compare_facts` and `run_what_if` compute, the model never does. II (no autonomous write-back): no approve or execute capability exists; proposals only. III (honest uncertainty): causal label is typed. IV (markings and roles): enforced in the port. VII (test-first, 80%): every task below starts with a failing test. No gate is relaxed.
