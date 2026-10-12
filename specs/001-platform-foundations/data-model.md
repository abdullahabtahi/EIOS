# Data Model: Platform Foundations (F00)

**Feature**: `001-platform-foundations` | **Date**: 2026-09-30 | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

Design-time description of the 11 key entities in the spec. All runtime models are immutable (frozen); updates create new instances. Field types are illustrative of shape, not a language binding. Numbers shown are `[ILLUSTRATIVE]` unless tagged otherwise.

## Conventions

- Identifiers are opaque strings; timestamps are UTC ISO-8601.
- Every entity that crosses a boundary is validated at that boundary (schema in `contracts/` where one exists).
- No entity holds secret values, raw personal data or ground-truth labels.

## 1. Environment

Where the platform runs: `dev`, `stage`, `prod-like`.

| Field | Type | Rules |
|---|---|---|
| name | enum | one of `dev`, `stage`, `prod-like` |
| project_ref | string | unique per environment `[ASSUMPTION]` |
| state_prefix | string | unique per environment; never shared |
| approval_required | bool | true for `prod-like` promotion |
| budget_thresholds | list of percent | 50, 80, 100 `[TARGET]` |

Relationships: owns many Service Identities; receives Pipeline Run Records; has one LLM Gateway Configuration.

Rule: no credential, bucket or state location is referenced by two environments (FR-013..FR-016).

## 2. Service Identity

| Field | Type | Rules |
|---|---|---|
| service | string | one identity per service |
| environment | ref Environment | required |
| roles | list of string | explicit, non-empty; wildcards and project-wide editor grants rejected |
| can_read_eval_truth | bool | false for all runtime services; true only for harness and pipeline identities |
| impersonable_by | list of workflow attributes | required for the release-candidate identity |

Relationships: belongs to one Environment.

## 3. Quality Gate

| Field | Type | Rules |
|---|---|---|
| id | string | e.g. `lint`, `types`, `coverage`, `contract`, `eval_smoke`, `red_line`, `vuln_scan`, `secret_scan`, `iac_plan` |
| blocking | bool | always true in F00 |
| stage | enum | `pr`, `merge`, `promote`, `release_candidate` |
| threshold | optional | e.g. coverage 80% `[TARGET]` |
| proof_fixture | path | faulty-change fixture that must fail this gate |

Rule: an empty registered-suite list yields "no suites registered", not a pass on unregistered suites (FR-006).

## 4. Pipeline Run Record

Schema: [contracts/pipeline-run-record.schema.json](./contracts/pipeline-run-record.schema.json).

| Field | Type | Rules |
|---|---|---|
| run_id | string | unique |
| commit_ref | string | revision or content hash when no git |
| workflow | enum | `pr`, `promote-stage`, `promote-prod-like`, `release-candidate` |
| gate_results | list of {gate_id, outcome, report_ref} | outcome `pass`, `fail`, `skipped_with_reason` |
| artefact_digests | list of string | images by digest |
| sbom_ref | optional string | required for release candidates |
| approver | optional string | from verified identity claims only |
| correlation_id | string | required |

State transitions: `started → gates_running → (passed | failed)`; `passed → promoted`. A failed run never transitions to `promoted`.

## 5. LLM Gateway Configuration

Schema: [contracts/llm-gateway-config.schema.json](./contracts/llm-gateway-config.schema.json).

| Field | Type | Rules |
|---|---|---|
| environment | ref Environment | required |
| provider | string | label; stub in F00 |
| model_id | string | no default; startup fails if absent in a deployed environment |
| prices | {input_per_unit, output_per_unit, currency} | each value carries a verification tag |
| rate_limits | map | each value tagged |
| daily_token_cap | integer | required; warn at 50/80%, block at 100% `[TARGET]` |
| verification | map value→tag | tag in `[BRIEF] [ASSUMPTION] [ILLUSTRATIVE] [TARGET] [SPIKE]`; `[SPIKE]` means unverified until S-01 closes |

Rule: values lacking a verification tag are rejected at load (FR-028).

## 6. LLM Call Trace

Schema: [contracts/llm-call-trace.schema.json](./contracts/llm-call-trace.schema.json).

| Field | Type | Rules |
|---|---|---|
| trace_id, correlation_id | string | required |
| prompt_id, prompt_version | string | must exist in `prompts.lock.json` |
| config_identity | string | hash of the configuration used |
| tokens_in, tokens_out | integer | non-negative |
| cost | number | derived from configured prices, never invented |
| latency_ms | integer | non-negative |
| outcome | enum | `ok`, `replay`, `unavailable`, `cap_reached` |
| replay_original_at | optional timestamp | present when outcome is `replay` |

No field carries raw prompt text containing secrets; redaction runs before emission.

## 7. Provenance Label

Defined in [contracts/provenance-labels.md](./contracts/provenance-labels.md) and `config/labels.yaml`.

| Field | Type | Rules |
|---|---|---|
| tag | enum | `[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]` |
| subject | text span | the figure or claim it qualifies |
| evidence | optional | brief citation, generator run (seed + revision + dataset hash) or eval report, when shown as a fact |

Rule: a numeric claim without a tag, or a real competitor brand name, fails the label check (FR-029..FR-031).

## 8. Decision Record

Template in `docs/spikes_and_adrs.md`; rules in [contracts/decision-and-spike-records.md](./contracts/decision-and-spike-records.md).

| Field | Type | Rules |
|---|---|---|
| id | string | `ADR-NNN` |
| title | string | required |
| status | enum | `Proposed`, `Accepted`, `Superseded by ADR-XXX` (index also allows `Open`) |
| date | date | required for record files |
| context, options, decision, consequences, evidence, revisit_when | text | required for `Accepted` |

State transitions: `Open → Proposed → Accepted → Superseded`. `Accepted` requires a record file; `Open` and `Proposed` may not have one.

## 9. Spike Record

| Field | Type | Rules |
|---|---|---|
| id | string | `S-NN` |
| question, method, data, result, decision, date | text | required to close |
| status | enum | `open`, `closed` |
| unlocks | list of ADR ids | a closed spike must link to an ADR |

Stored beside its ADR in `docs/adr/`.

## 10. Cost Model Entry

Rules in [contracts/cost-model.md](./contracts/cost-model.md); stored in `docs/cost_model.csv`.

| Field | Type | Rules |
|---|---|---|
| driver | string | e.g. compute, storage, LLM tokens |
| unit, quantity, unit_price | text/number | quantity and price carry a tag |
| price_source | string | required |
| price_verified_on | date | required; stale beyond the configured age fails the check `[TARGET]` |
| tag | enum | provenance tag |

## 11. Feature Dependency Declaration

Schema: [contracts/feature-dependencies.schema.json](./contracts/feature-dependencies.schema.json).

| Field | Type | Rules |
|---|---|---|
| feature | string | e.g. `F03` |
| depends_on_features | list | must be earlier features |
| depends_on_spikes | list of `S-NN` | each must be closed with an ADR before the feature starts |
| depends_on_adrs | list of `ADR-NNN` | each must be `Accepted` |

Rule: `tools/readiness` fails if any listed spike is open or any listed ADR is not `Accepted` (FR-034).

## Relationship summary

```text
Environment 1--* Service Identity
Environment 1--1 LLM Gateway Configuration
Environment 1--* Pipeline Run Record --* Quality Gate results
LLM Gateway Configuration 1--* LLM Call Trace
Decision Record 1--* Spike Record (unlocks)
Feature Dependency Declaration --* Spike Record / Decision Record
Provenance Label / Cost Model Entry: standalone, checked by tools
```

## Planned deviations from initial design

The following implementation details differ from this design model, as introduced during F00:
- **Service Identity**: Identities are declared centrally in `infra/identities.yaml` (T086).
- **Quality Gate**: Gates are defined centrally in `config/gates.yaml` (T042) and gate quarantine in `config/quarantine.yaml` (T047).
- **Feature Register**: Feature readiness is tracked in `docs/feature_register.yaml` (T174), alongside the dependency declarations.
