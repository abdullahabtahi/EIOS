# Quickstart: F00 Platform Foundations — Validation Guide

**Feature**: `001-platform-foundations` | **Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

This is a validation guide, not an implementation guide. It says how to prove each success criterion once F00 is built. Entry-point names in angle brackets are placeholders that F00's implementation defines and documents (FR-003); no command below exists yet, and none should be assumed.

## Prerequisites

- A workstation with the toolchain named in `research.md` (R-01..R-20; versions verified at implementation `[SPIKE]`).
- Three empty cloud accounts or projects, one per environment `[ASSUMPTION]`, plus the bootstrap stack applied once by hand (the single documented manual exception, R-05).
- No real LLM credentials. F00 runs on the stub provider only.
- A clean checkout, or a content-hash revision id if the directory is not yet a git repository.

## Scenarios

Each scenario lists what to do, what to observe, and the criterion it proves. Contracts referenced: [gateway interface](./contracts/llm-gateway-interface.md), [gate registry](./contracts/gate-hook-registry.md), [labels](./contracts/provenance-labels.md), [decisions and spikes](./contracts/decision-and-spike-records.md), [cost model](./contracts/cost-model.md).

### 1. Gates fail on faulty changes and pass on clean ones (SC-001, US1)

1. Run the `pr` pipeline on a clean change. Expect every FR-004 gate `pass` on the Pipeline Run Record.
2. For each gate, apply its faulty-change fixture (style violation, type error, coverage drop below 80% `[TARGET]`, broken data contract, failing smoke eval, failing registered Red-Line suite, known-vulnerable dependency, planted secret-shaped string, invalid infrastructure definition).
3. Expect each run `failed`, that gate `fail`, and no merge possible. Record shows the gate id and report reference.
4. With the registry empty, expect "no suites registered" and a pass; register a failing stub suite and expect a fail ([gate registry](./contracts/gate-hook-registry.md)).

### 2. Local setup in under 30 minutes (SC-002, US1)

1. On a fresh machine, follow only the documented setup in the repository.
2. Run the single local check entry point `make check`; it runs the same gates as the pipeline.
3. Time from clone to green. Target under 30 minutes `[TARGET]`; log the result as evidence.

### 3. Environments recreate from an empty account (SC-003, US2)

1. After bootstrap, apply the infrastructure definitions for `dev`, `stage`, `prod-like` from the repository only.
2. Destroy and recreate one environment.
3. Expect zero manual steps and an empty drift report on the plan after recreate.
4. Confirm no resource or credential is shared across environments and that `prod-like` keeps at least one instance of each stateful service and uses real key management for signing.

### 4. Secrets and identity (SC-004, US2)

1. Run the secret scan over the working tree, history, built images and captured logs; expect zero findings.
2. List service identities; expect one per service, each with a reviewed least-privilege grant. Introduce a shared identity in a test change and expect review to fail.
3. Rotate a secret in the managed store and confirm the service picks it up without a code change.
4. Confirm the ground-truth location cannot be read by any service or model identity, only by the evaluation harness and pipeline identity.

### 5. LLM gateway on the stub provider (SC-005, SC-006, US3)

1. Run the gateway contract tests: `ok`, `replay`, `unavailable` and `cap_reached` are each reachable ([interface](./contracts/llm-gateway-interface.md)).
2. Force the provider unavailable with an empty replay store; expect `unavailable` and no text.
3. Warm the replay store, force an outage; expect `replay` with an original timestamp.
4. Raise usage to the 50% and 80% thresholds `[TARGET]`; expect warning events. Reach 100%; expect `cap_reached` and no provider call.
5. Inspect traces: every call has one, matching [llm-call-trace.schema.json](./contracts/llm-call-trace.schema.json), and none contains secret-shaped strings.
6. Change model, price or cap by configuration only; expect the change to take effect without a code change. Remove a verification tag from a configured value; expect startup failure.
7. Run the automated search for model identifiers, prices and provider names in application code; expect zero matches outside configuration and `providers/` (SC-006).

### 6. Labels and provenance enforced (SC-007, US4)

1. Run `label_check` over F00 documents; expect a pass with a scanned-file count.
2. Run it over the seeded test document with unlabelled figures, a `[BRIEF]` claim without citation, a `[SPIKE]` claim without a spike id, and a planted competitor brand name and version pin; expect each flagged with file and line and 100% recall `[TARGET]`.
3. Add an allowlist entry with an empty reason; expect rejection.

### 7. Decisions, spikes and readiness (SC-008, SC-011, US5)

1. Run `adr_check` on the ADR index and files; expect agreement. Introduce each mismatch class from the [contract](./contracts/decision-and-spike-records.md) and expect failure.
2. Declare a feature dependency on an open spike; expect `readiness` to report it blocked and list the spike ([schema](./contracts/feature-dependencies.schema.json)).
3. Close the spike with an accepted ADR; expect `readiness` to report ready on the next run.
4. Run `open_decision_check`; expect ADR-002, 003, 009 and 014 all still open and no F00 artefact fixing their outcome. Plant a vendor SDK import and expect failure.

### 8. Rollback (SC-009, FR-010)

1. Promote a revision to `stage`, then promote a second one.
2. Roll back by redeploying the previous revision and toggling configuration.
3. Record the elapsed time against the documented bound `[TARGET]`; this must be done at least once before any `prod-like` promotion.

### 9. Correlation, observability and cost (SC-010, US6)

1. Send one request through `skeleton_edge` to `skeleton_core`; expect the same correlation identifier in both services' traces and logs.
2. Confirm each skeleton has an SLO placeholder, a runbook stub, and a warm-start statement where it holds in-memory state (FR-039).
3. Run `cost_check`; expect a pass, totals over verified rows only, and every figure showing source, pricing date and label ([cost model](./contracts/cost-model.md)).
4. Inspect each environment's infrastructure plan for budget alerts at 50%, 80% and 100% `[TARGET]`; trigger one threshold in `dev` and confirm the alert fires.

## Coverage map

| Criterion | Scenario |
|---|---|
| SC-001 | 1 |
| SC-002 | 2 |
| SC-003 | 3 |
| SC-004 | 4 |
| SC-005, SC-006 | 5 |
| SC-007 | 6 |
| SC-008, SC-011 | 7 |
| SC-009 | 8 |
| SC-010 | 9 |

## Evidence

Every run above writes a Pipeline Run Record ([schema](./contracts/pipeline-run-record.schema.json)) and stores reports under `evals/reports/`. A scenario passes only when its evidence is on record, not when it was observed once by hand.
