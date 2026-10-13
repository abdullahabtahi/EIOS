# Data Model: Agent Quality Gates

All records are frozen (immutable) and validated at the boundary when loaded. Field names are the contract; storage is files.

## TurnRecord (one evaluated turn)

| Field | Type | Rule |
|---|---|---|
| `record_id` | string | Unique; `<case_id>.<repeat>` for suite runs |
| `case_id` | string or null | Null for live production turns |
| `repeat` | int, 0-based | |
| `runtime` | string | `copilot`, `adk`, `standin:<name>` |
| `session_id` | string | |
| `turn_index` | int, 1-based | |
| `operator_id` | string | Pseudonymous; from the verified identity when the runtime supports it |
| `identity_source` | `verified_token` or `request_body` or `none` | `request_body` is reported as a defect (B3) |
| `role` | enum | The five workstation roles |
| `entity_context` | object or null | Entity id and type the UI supplied |
| `question` | string | |
| `tool_calls` | list of ToolCall | Ordered |
| `rounds` | int | Model rounds used, including corrections |
| `answer` | string | Final text shown to the operator |
| `bindings` | list of Binding or null | Present only when the runtime emits reference answers |
| `citations` | list of string | |
| `is_replay_fallback` | bool | |
| `fallback_reason` | string or null | Required when `is_replay_fallback` is true |
| `audit_verdict` | string or null | The runtime's own verdict, recorded, never trusted |
| `data_origin` | `fixture` or `live` | Declared by the runtime; `fixture` is shown in the report |
| `latency_ms` | float | |
| `tokens_in`, `tokens_out`, `cost_usd` | numbers or null | Null when the runtime cannot report them |
| `outcome` | `completed`, `inconclusive` | `inconclusive` carries `inconclusive_reason` |

**ToolCall**: `name`, `capability` (resolved id or null), `arguments` (object), `result` (object or null), `error` (typed code or null), `latency_ms`, `untrusted` (bool).

**Binding**: `span` (start, end in `answer`), `fact_ref` (tool call index and field path), `unit`.

**Invariants**: `fallback_reason` present iff `is_replay_fallback`; `result` xor `error` per call; `inconclusive` records are never judged `pass`.

## Fact (derived, not stored)

`path` (tool call index and JSON path), `value` (normalised number), `unit_family` (count, currency, percent, multiplier, basis points, duration, other), `label_tokens` (words from the path and per-case aliases), `as_of`. Built by `core/facts.py` from `ToolCall.result`.

## FigureVerdict (per figure in an answer)

`text`, `span`, `value`, `unit_family`, `verdict` (`supported`, `unsupported`, `exempt`), `reason` (`ok`, `no_matching_value`, `wrong_scale`, `wrong_unit`, `wrong_field`, `ambiguous`, `derived`, `exempt:<category>`), `matched_fact` (path or null), `candidates` (paths considered).

## GoldenCase (extends the dialogue scenario)

`case_id`, `workstation`, `split` (dev, validation, sealed), `turns[]` where each turn has `user_query`, `expected_capabilities[]` (ordered, with allowed extras), `forbidden_capabilities[]`, `expected_facts[]` (capability plus field path plus unit), `aliases` (label synonyms for the faithfulness check), `refusal_required`, `max_rounds`, `data_origin_expected`, and `repeats`. Rejected at load if any agent-visible field contains ground-truth material.

## AttackCase

`case_id`, `family` (injection_via_tool_text, stage_then_self_approve, direct_write_attempt, identity_or_role_impersonation, cross_scope_request), `paraphrased` (bool, true when it avoids the known blocklist substrings), `setup` (question, role, optional `tool_fixtures`, optional canary), `must_not` (list of observable outcomes such as `call:approve_action`, `call:propose_*_after_injection`, `answer_contains_canary`, `identity_changed`), `repeats` (default 3).

## Capability

`id` (for example `aml.dossier`, `metric.get`, `knowledge.regulation`, `action.propose`), `kind` (evidence, knowledge, compute, draft, propose), and a per-runtime map: `copilot` tool name or `unavailable`, `target` tool name from `docs/agent-architecture.md`, or `unavailable`. `unavailable` yields `capability_missing`, reported not passed.

## Verdict and GateResult

`Verdict`: `pass`, `fail`, `inconclusive`, with `evidence` (the record id, the figure or call that decided it). `GateResult`: gate id, `blocking`, counts per verdict, the first failing case with its evidence, `proven` (false when inconclusive cases remain), and thresholds from configuration.

## BaselineReport

Header (git sha, date, runtime, data split, model configuration name, repeat count, spend), then per workstation: faithfulness rate (M3), p95 latency and cost per turn (M5), trajectory pass rate, capability coverage, red-line results, attack results split into keyword and paraphrased, share of turns on fixture data, share with request-body identity. Failures listed with evidence. Measured numbers are tagged `[MEASURED]`; anything not measured is not shown.

## TelemetryEvent

`event_id`, `ts`, `operator_token`, `session_token`, `runtime`, `role`, `tool_call_count`, `tool_names`, `rounds`, `latency_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `is_replay_fallback`, `fallback_reason`, `audit_verdict`, `citation_count`, `data_origin`, `question_excerpt` (bounded, redacted), `case_id` (null in production). Derived by pure function from a TurnRecord; a scanner rejects any value that matches the raw-identifier patterns.

## State transitions

`TurnRecord.outcome`: created `completed` or `inconclusive`; never mutated. A `GateResult` is `proven` only when every dependent case is `completed`.
