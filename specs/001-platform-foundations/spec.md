# Feature Specification: Platform Foundations (F00)

**Feature Branch**: `001-platform-foundations`
**Created**: 2026-09-29
**Status**: Draft
**Input**: User description: "F00-foundations: the engagement's foundational platform layer that every other feature depends on. Scope per initial_plan.md §3, §8 (slice S0), §10 and docs/engagement_plan.md: repository structure and conventions, infrastructure as code for the dev, stage and prod-like environments, CI/CD pipeline skeleton with blocking gates (lint, type check, tests with 80% coverage, contract tests, eval smoke, Red-Line suite hook, vulnerability scan), secret management and per-service identity, a provider-neutral LLM gateway with token caps whose model choice stays open (ADR-002, spike S-01), the labelling and provenance conventions, and the ADR and spike record workflow in docs/adr/. Explicitly out of scope: any specific LLM, metric engine, frontend stack or API surface choice (ADR-002, 003, 009, 014 stay open); no business features. Reference constitution principles V, VI, VIII and the Engineering Constraints. The spec must describe WHAT and WHY for the platform's users (engineers, reviewers, an FDE team), not implementation technology."

**Constitution references**: Principle V (Provenance and Labelling), Principle VI (Eval-First, Anti-Circularity), Principle VIII (Deterministic Fallback and Operability), and the Engineering Constraints section (secrets and identity, provider neutrality, immutability and structure, validation at boundaries, infrastructure as code, open decisions stay open).

**Labelling regime**: figures in this document carry the tags defined in Principle V. `[TARGET]` marks a commitment to measure, not a claim of achievement. `[ASSUMPTION]` marks a default that a later phase may revise.

## Users of the Platform

- **Engineer**: builds features F01–F15 on top of this layer.
- **Reviewer**: reviews changes and evidence, and decides what may merge or be promoted.
- **FDE Team Lead**: owns environments, cost, risk and the phase-gate reports for the engagement.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every change passes blocking quality gates (Priority: P1)

An engineer proposes a change. Before a reviewer or any environment sees it, an automated pipeline runs the same set of checks for every change and blocks the change if any check fails: style and static analysis, type checking, unit tests with the minimum coverage, data-contract tests, an evaluation smoke run, the Red-Line suite hook, a dependency and container vulnerability scan, secret scanning, and validation of the infrastructure definitions.

**Why this priority**: Every later feature inherits its quality bar from this pipeline. Without it, the constitution's blocking-gate rules (Principle VI, Delivery Workflow) cannot be enforced, and nothing else can be trusted.

**Independent Test**: Submit deliberately failing changes (one per gate) to an empty skeleton project and confirm that each is blocked with a clear reason, and that a clean change passes.

**Acceptance Scenarios**:

1. **Given** a change that breaks a style, type, or unit-test rule, **When** the pipeline runs, **Then** the change is marked non-mergeable and the failing gate and reason are shown.
2. **Given** a change that lowers unit-test coverage below the minimum, **When** the pipeline runs, **Then** the change is blocked and the measured coverage is reported.
3. **Given** a change that introduces a known-vulnerable dependency or container layer, **When** the pipeline runs, **Then** the change is blocked and the finding is listed with its severity.
4. **Given** a change that adds a credential-like string, **When** the pipeline runs, **Then** the change is blocked before merge.
5. **Given** the eval smoke and Red-Line hooks exist but no suites have been authored yet, **When** the pipeline runs, **Then** the hooks execute, report "no suites registered", and fail the run if a suite later becomes registered and fails.
6. **Given** a change that passes every gate, **When** it is merged, **Then** it is promoted to `stage`, and promotion to `prod-like` requires a recorded human approval.

---

### User Story 2 - Isolated, reproducible environments with least-privilege identity (Priority: P1)

An FDE team lead can create, inspect and destroy the `dev`, `stage` and `prod-like` environments from version-controlled definitions alone. Each environment is isolated from the others. Every service runs with its own identity holding only the access it needs, and no secret ever lives in the repository.

**Why this priority**: The engagement's credibility depends on "reproducible from scratch" and on showing production discipline (Engineering Constraints: secrets and identity, infrastructure as code). Later features cannot be deployed or safely tested without it.

**Independent Test**: From a clean account, create all three environments from the repository, confirm they are isolated, confirm each service identity can reach only its declared resources, then destroy and recreate one environment and compare it to the original.

**Acceptance Scenarios**:

1. **Given** the repository and an empty cloud account, **When** the team lead applies the environment definitions, **Then** `dev`, `stage` and `prod-like` exist with the documented differences (data seeds allowed, stubs allowed, sealed-holdout access, minimum-instance policy).
2. **Given** a service identity in `dev`, **When** it attempts to reach a `stage` or `prod-like` resource, **Then** the access is denied and the attempt is logged.
3. **Given** a service, **When** its identity is inspected, **Then** it is unique to that service and its granted access matches a reviewed, declared list.
4. **Given** the repository history and working tree, **When** a secret scan runs, **Then** no secrets are found and every runtime secret is retrieved from the managed secret store at run time.
5. **Given** a planned infrastructure change, **When** a reviewer opens the change, **Then** they see a plan of exactly what will be created, altered or destroyed before approval.
6. **Given** an environment is torn down and recreated, **When** compared with its previous state, **Then** there is no undeclared drift.

---

### User Story 3 - Provider-neutral LLM access with caps, traces and safe degradation (Priority: P1)

An engineer building an agent calls a single platform access point for language-model requests. The access point hides which provider and model are in use, enforces a per-day token cap, records a trace for every call, and returns a clearly labelled cached result if the provider is unavailable. Model choice, pricing and limits are configuration, not code, and stay open until spike S-01 closes with ADR-002. A stubbed provider is available for development and CI.

**Why this priority**: Every agent feature depends on it, and ADR-002 must stay open. Without a neutral seam, the first agent feature silently decides the LLM. Principle VIII requires deterministic fallback; the Engineering Constraints require provider neutrality and token caps.

**Independent Test**: With only the stub provider configured, run calls until the cap is reached, simulate a provider outage, and confirm the cap enforcement, the fallback labelling and the per-call trace, all with no real provider credentials.

**Acceptance Scenarios**:

1. **Given** the stub provider is configured, **When** a request is made, **Then** a deterministic response is returned and a trace record is written.
2. **Given** the daily token cap is reached, **When** another request is made, **Then** it is refused with a clear, non-silent "cap reached" outcome and the event is recorded and alerted.
3. **Given** a provider outage, **When** a request that has a prior cached result is made, **Then** the cached result is returned and labelled as a replay; **When** no cached result exists, **Then** the caller receives an explicit "unavailable" outcome and never an invented answer.
4. **Given** the model, pricing and cap values are changed in configuration, **When** the next request is made, **Then** the new values apply without any code change.
5. **Given** any call, **When** its trace is inspected, **Then** it shows the prompt version, model identifier, token counts, latency, cost, correlation identifier and outcome.
6. **Given** the repository, **When** it is searched, **Then** no model identifier, price or provider is hard-coded in application code.

---

### User Story 4 - Labels and provenance are enforced, not optional (Priority: P2)

A reviewer checking any document, report or UI-bound figure can see its label and its provenance. The platform provides the tag vocabulary, a machine-checkable convention, and a review-time check that fails when a figure or claim is unlabelled or an evidence pointer is missing.

**Why this priority**: Principle V makes provenance the basis of portfolio credibility. It is P2 because it protects the value of everything else, but the pipeline and environments must exist first.

**Independent Test**: Add a document containing an unlabelled number, a `[BRIEF]` figure without a citation, and a `[SPIKE]` claim with no spike reference; confirm the check flags all three, and passes when corrected.

**Acceptance Scenarios**:

1. **Given** a document with a number carrying no tag, **When** the label check runs, **Then** it fails and identifies the location.
2. **Given** a `[BRIEF]` claim, **When** the check runs, **Then** it requires a citation into `docs/brief/`.
3. **Given** a claim tagged `[SPIKE]`, **When** the check runs, **Then** it requires a spike identifier and reports whether that spike is closed.
4. **Given** a figure claimed to come from a generator run or evaluation report, **When** the check runs, **Then** it requires the seed, code revision and dataset hash, or a report reference.

---

### User Story 5 - Decisions and spikes have a durable, enforceable record (Priority: P2)

An engineer or reviewer can record an architecture decision or a time-boxed spike in a fixed format in `docs/adr/`, see the status of every decision in one index, and find out whether a feature is allowed to start. A feature that depends on an unresolved spike is blocked until the spike closes with an accepted decision.

**Why this priority**: The constitution requires spikes before dependence (Delivery Workflow) and keeps ADR-002, 003, 009 and 014 open. Without a workflow those decisions get made accidentally by code.

**Independent Test**: Create a spike record and a dependent feature marker; confirm the dependent feature is reported as blocked, close the spike with an ADR, and confirm it is reported as unblocked.

**Acceptance Scenarios**:

1. **Given** a new decision, **When** the engineer uses the provided template, **Then** the record contains status, date, context, options with honest drawbacks, decision, consequences, evidence and revisit-when.
2. **Given** a spike record, **When** it is completed, **Then** it contains question, method, data, result, decision and date, and lives beside its ADR.
3. **Given** a feature that declares a dependency on a spike, **When** the spike is open, **Then** the readiness check reports the feature as blocked and names the spike.
4. **Given** the ADR index, **When** any record changes status, **Then** the index reflects it, and a check fails if the index and files disagree.
5. **Given** any change that names a specific LLM, metric engine, frontend stack or API surface in a specification or code path, **When** the corresponding ADR is still open, **Then** the review check flags it.

---

### User Story 6 - Observability and cost visibility from day one (Priority: P3)

The FDE team lead can follow a request across services with one correlation identifier, view versioned prompts as artefacts, and see a component-level cost model with budget alerts and the daily token cap. Every cost figure carries a pricing date and label.

**Why this priority**: Principle VIII requires operability and the engagement plan requires cost discipline, but the skeleton can arrive after gating and environments.

**Independent Test**: Send one request through two skeleton services and confirm one correlation identifier appears in both traces; trigger a budget threshold and confirm the alert fires.

**Acceptance Scenarios**:

1. **Given** a request that crosses two services, **When** traces are viewed, **Then** they share one correlation identifier.
2. **Given** a prompt is changed, **When** it is committed, **Then** it has a new version, and traces reference the version used.
3. **Given** spend reaches 50%, 80% and 100% of budget `[TARGET]`, **When** each threshold is crossed, **Then** an alert is raised.
4. **Given** the cost model, **When** any figure is inspected, **Then** it shows its source, pricing date and label.

---

### Edge Cases

- The daily token cap is exhausted mid-day: further calls are refused visibly, cached replays remain allowed, and the cap resets at a documented boundary.
- Provider outage with no cached result: the caller gets an explicit "unavailable" outcome; nothing is fabricated.
- A secret is committed by accident: the change is blocked before merge; if it reaches history, a documented rotate-and-purge procedure applies and the incident is recorded.
- A vulnerability appears in a dependency between merge to `stage` and promotion to `prod-like`: promotion is blocked until it is resolved or risk-accepted in a recorded exception.
- A `[SPIKE]` claim is used before its ADR closes: the label check and readiness check flag it, and the dependent feature stays blocked.
- Sealed-seed results requested outside CI or on a non-release-candidate build: the request is refused; sealed results are produced only by CI on release candidates.
- A contributor reaches for a technology tied to an open ADR: the review check flags it and directs them to the ADR.
- A gate is flaky: it is quarantined with an owner and expiry date, never silently disabled.
- Two environments accidentally share a resource or credential: environment isolation checks fail the run.
- The pipeline itself is unavailable: no manual bypass exists; promotion waits or follows a recorded emergency procedure with retroactive review.

## Requirements *(mandatory)*

### Functional Requirements

**Repository and conventions**

- **FR-001**: The repository MUST define a documented structure and conventions covering where code, contracts, evaluations, infrastructure definitions, prompts, documents and decision records live, so any engineer can locate them without guidance.
- **FR-002**: The conventions MUST encode the constitution's structure rules (focused files with a documented size ceiling, small functions, immutable-by-default data, explicit error handling, validation at every external boundary) and the pipeline MUST check those that can be checked automatically.
- **FR-003**: The repository MUST provide a documented, single-command way to set up a working local (`dev`) setup and to run the same checks the pipeline runs.

**Quality gates and delivery pipeline**

- **FR-004**: Every proposed change MUST run the same blocking gates: style and static analysis, type checking, unit tests with at least 80% coverage `[TARGET]`, data-contract tests, evaluation smoke run on dev seeds, the Red-Line suite hook, dependency and container vulnerability scan, secret scan, and infrastructure-definition validation with a plan.
- **FR-005**: A change MUST NOT be mergeable while any blocking gate fails; there MUST be no bypass that leaves no record.
- **FR-006**: The contract-test, evaluation-smoke and Red-Line gates MUST exist as registered hooks that later features fill in; an empty hook MUST report explicitly that no suites are registered and MUST start failing the pipeline as soon as a registered suite fails.
- **FR-007**: Merge to the main line MUST promote automatically to `stage` and run the validation-seed evaluations and a lightweight resilience check as their suites appear; promotion to `prod-like` MUST require a recorded human approval.
- **FR-008**: Release candidates MUST be the only builds allowed to trigger sealed-seed evaluation, and sealed results MUST NOT be retrievable by any other path (Principle VI).
- **FR-009**: The pipeline MUST record, per run, the code revision, gate results, coverage, findings and approver, and keep them for later evidence.
- **FR-010**: Every promotion MUST be reversible by redeploying the previous revision and toggling configuration, and the rollback MUST be exercised at least once before the first prod-like promotion `[TARGET]`.
- **FR-011**: Builds MUST use pinned dependency manifests, and every build MUST produce a software bill of materials. Unverified library, model or price pins are forbidden and MUST be tagged `[SPIKE]` until verified.
- **FR-012**: Flaky gates MUST be quarantinable only with a named owner and expiry, and the number of quarantined gates MUST be visible.

**Environments, secrets and identity**

- **FR-013**: All cloud resources MUST be declared in version-controlled definitions; no resource may be created by hand.
- **FR-014**: The platform MUST provide three isolated environments, `dev`, `stage` and `prod-like`, with documented differences, and no resource or credential shared across them (`[ASSUMPTION]`: one isolated cloud project per environment).
- **FR-015**: `prod-like` MUST keep at least one running instance of stateful services and MUST use real key-management for signing, as required by the engagement plan.
- **FR-016**: Each service MUST have its own identity with least-privilege access declared in reviewed definitions; a shared identity MUST fail review.
- **FR-017**: Secrets MUST be stored only in the managed secret store, be retrieved at run time, and be rotatable without a code change. No secret may appear in the repository, images, logs or traces.
- **FR-018**: Approver and user identity for any future governed action MUST come from the identity provider's verified claims and MUST NOT be accepted from a request body (foundation provided here; used by later features).
- **FR-019**: The platform MUST provide a separate, access-restricted location for evaluation ground truth that agents, models at inference, and the user interface can never read; only the evaluation harness and pipeline identity may read it (Principle VI).
- **FR-020**: Free text from external sources (tickets, communications, documents) MUST be treated as untrusted data by convention and by shared validation helpers available to all features.

**LLM gateway**

- **FR-021**: The platform MUST provide one provider-neutral access point for all language-model calls; no feature may call a provider directly.
- **FR-022**: Model identifiers, prices, rate limits, and per-day token caps MUST be configuration only, never hard-coded, and MUST be marked `[SPIKE]` until verified by spike S-01.
- **FR-023**: The access point MUST enforce a per-day token cap and refuse further calls with an explicit outcome once reached, and MUST alert when usage crosses configurable thresholds.
- **FR-024**: The access point MUST record a trace for every call: prompt version, model identifier, token counts, latency, cost, correlation identifier, tool calls if any, verdict of any downstream check, and outcome.
- **FR-025**: On provider outage, the access point MUST return a previously cached result clearly labelled as a replay, or an explicit "unavailable" outcome; it MUST NEVER return an invented answer (Principle VIII).
- **FR-026**: A deterministic stub provider MUST be available for `dev` and CI so that all tests and pipeline gates run with no real provider and no real credentials.
- **FR-027**: The access point MUST validate its inputs and outputs against a schema at the boundary and treat provider output as untrusted.
- **FR-028**: The platform MUST NOT, in this feature, select any specific model or provider as the default; the choice remains open until ADR-002 is accepted.

**Labelling and provenance**

- **FR-029**: The platform MUST provide the tag vocabulary (`[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]`) and a documented convention for attaching provenance to a figure (brief citation, generator run with seed, code revision and dataset hash, or evaluation report reference).
- **FR-030**: A review-time check MUST flag unlabelled numeric claims in specifications, reports and case-study documents, `[BRIEF]` claims lacking a brief citation, `[SPIKE]` claims lacking a spike reference, and figures claiming a generator or eval origin without the required references.
- **FR-031**: The check MUST flag real brand names used as competitors and unverified version or price pins.

**Decision and spike workflow**

- **FR-032**: The platform MUST provide ADR and spike templates matching the templates in `docs/spikes_and_adrs.md`, stored in `docs/adr/` with `NNN-title.md` naming, and a single index of statuses.
- **FR-033**: A feature MUST be able to declare its dependencies on spikes and ADRs, and a readiness check MUST report it as blocked while any such spike is open.
- **FR-034**: A consistency check MUST fail when the ADR index and the records disagree, or when a record lacks a required field.
- **FR-035**: A check MUST flag specifications or code that assume an outcome of an open decision (ADR-002, 003, 009, 014) while it remains open.

**Observability and cost**

- **FR-036**: Every service skeleton MUST emit traces and logs carrying a correlation identifier that is preserved across service boundaries.
- **FR-037**: Prompts MUST be versioned artefacts in the repository, and every trace MUST reference the prompt version used.
- **FR-038**: The platform MUST provide a component-level cost model file with source and pricing date for every figure, budget alerts at 50%, 80% and 100% of budget `[TARGET]`, and reconciliation against the actual bill once available.
- **FR-039**: Each service skeleton MUST have a documented service-level objective placeholder, a runbook stub, and a documented warm-start statement if it holds in-memory state, filled in by the owning feature.

### Key Entities

- **Environment**: a named, isolated deployment target (`dev`, `stage`, `prod-like`) with declared differences in data seeds, stubs, sealed-holdout access and minimum-instance policy.
- **Service Identity**: the unique least-privilege identity of one service, with a reviewed list of granted access.
- **Quality Gate**: a blocking check with a name, owner, pass criteria, and result recorded per pipeline run; may be a registered hook awaiting suites.
- **Pipeline Run Record**: revision, gate results, coverage, findings, approver and timestamp for a change or promotion.
- **LLM Gateway Configuration**: models, prices, rate limits, caps and thresholds by role; all values configuration and each tagged with its verification state.
- **LLM Call Trace**: one record per call with prompt version, model identifier, token counts, latency, cost, correlation identifier, outcome and any fallback replay label.
- **Provenance Label**: a tag from the fixed vocabulary plus the reference that supports it (citation, run manifest, or report).
- **Decision Record (ADR)**: a numbered record with status, context, options, decision, consequences, evidence and revisit condition.
- **Spike Record**: a time-boxed investigation with question, method, data, result, decision and date, linked to the ADR it unlocks.
- **Cost Model Entry**: a component-level cost line with source, pricing date, label and reconciliation status.
- **Feature Dependency Declaration**: the list of spikes and ADRs a feature needs before it may start.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the blocking gates listed in FR-004 are demonstrated to fail on a deliberately faulty change and pass on a clean one, before any F01+ feature is merged.
- **SC-002**: An engineer with no prior context can set up the local environment and run the full local check suite in under 30 minutes `[TARGET]`, measured with one fresh-start dry run.
- **SC-003**: All three environments can be created from an empty account and destroyed using only repository contents, with zero manual steps and zero undeclared drift after a recreate.
- **SC-004**: 0 secrets are found in the repository, history, images and logs by scanning at every pipeline run, and 100% of services have a unique identity.
- **SC-005**: With the stub provider only, 100% of LLM gateway acceptance scenarios (cap enforcement, outage fallback, tracing, configuration-only change) pass with no real credentials.
- **SC-006**: 0 model identifiers, prices or provider names are hard-coded in application code, verified by an automated search at every run.
- **SC-007**: 100% of numeric claims in F00 documents carry a label, and a seeded test document with unlabelled figures is flagged with 100% recall `[TARGET]`.
- **SC-008**: A feature that declares a dependency on an open spike is reported as blocked in 100% of test cases, and unblocks within one check run of the spike closing with an ADR.
- **SC-009**: A rollback of the previous revision is exercised successfully at least once, completing within a documented time bound `[TARGET]`.
- **SC-010**: One correlation identifier is visible end to end across at least two skeleton services for a single request.
- **SC-011**: The four open decisions (ADR-002, 003, 009, 014) remain open at the end of F00: no artefact of F00 fixes their outcome.

## Assumptions

- `[ASSUMPTION]` One isolated cloud project per environment is used; the number is revisitable in the plan phase.
- F00 delivers foundations and hooks only. Data contracts, generators, ontology, metric registry and evaluation suites are owned by F01–F04; the F00 gates run against empty or skeleton content until those features supply it.
- ADR-002 (LLM), ADR-003 (metric engine), ADR-009 (frontend), ADR-014 (API surface) remain open. F00 provides the seams that let those decisions land later without rework.
- The tag vocabulary and provenance rule are as defined by constitution Principle V and `docs/synthetic_data_strategy.md` §2.
- The Red-Line tests RL-1..RL-7 are defined in `docs/models_and_evals.md` §6; F00 provides only the hook and execution path, not the tests.
- Pipeline, environment and cost targets in `docs/engagement_plan.md` are inputs; any figure reused from there keeps its original label.
- No business features, user-facing cockpit or customer data are part of F00. All data used by F00 tests is synthetic or trivial fixture data.
- The engagement is a simulation: "approval" and "on-call" are exercised by the FDE team in rehearsal, not by a real operations organisation.
