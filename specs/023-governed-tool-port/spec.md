# Feature Specification: Governed Tool Port

**Feature Branch**: `023-governed-tool-port`

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "One typed, governed set of capabilities that both the workstations and the assistant use, so the assistant agrees with the screen, can only do what its role allows, and can never approve or execute. Replace the fixture tool set and the unstructured duplicates with a single catalogue; keep governance records out of the analytics store."

**Context**: `EIOS/docs/adr/018-bounded-contexts-and-governed-tool-surface.md` (Proposed), `docs/agent-architecture.md` (sections 1, 2 and 9), `docs/data-strategy.md` (R1 to R4), `specs/022-agent-quality-gates` (the gates that prove this feature). Constitution principles I, II, III, IV and VII apply.

## Why this exists

An operator looking at the partner workstation sees a churn hazard of 78%; the assistant, asked about the same partner, says 0.84, names a different root cause, and proposes an action called `DISPATCH_RETENTION_PLAYBOOK`. They disagree because they read different data through different code: the assistant has its own small fixture tool set, the workstation has its own payloads, and the governed tool server that was meant to sit between agents and data (42 handlers, called by name, several duplicates, none with typed inputs and outputs) is bypassed. Partner ids differ between layers (`PTR-882`, `P-882`, `AP-1029` for the same story). Governance records share a database with analytics. This feature builds the one governed surface that fixes all of that.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The assistant states what the AML workstation shows (Priority: P1)

An AML investigator looks at an alert dossier and asks the assistant about the same account. The figures, the timeline, the network and the withdrawal-risk assessment the assistant cites are exactly the ones the workstation shows, because both are served by the same typed capabilities. Every result says what it is, its unit, when it was true, where it came from and whether it is demo data.

**Why this priority**: The AML flow is the lighthouse (`docs/lighthouse.md`). An assistant that contradicts the screen is unusable, and an unreliable figure is the failure that destroys trust fastest.

**Independent Test**: For the golden AML entities, compare the figures the assistant can state with the workstation's payload. Delivers value alone: the AML slice of the assistant becomes trustworthy even if nothing else is done.

**Acceptance Scenarios**:

1. **Given** an account shown with a 16x turnover discrepancy on the workstation, **When** the assistant is asked about it, **Then** its answer uses the same 16x figure, with the same as-of time and data origin.
2. **Given** a capability result for an account, **When** it is inspected, **Then** it contains the value, unit, as-of time, data origin, source pointer and security marking for every figure.
3. **Given** an account id that does not exist, **When** any capability is called with it, **Then** the result is a typed "not found", never a default or neighbouring entity.

---

### User Story 2 - Safe by construction (Priority: P1)

A compliance head needs to know that the assistant can read and propose but can never approve or execute, that each role sees only what its markings allow, and that text from outside the system cannot steer it. This is enforced where the capabilities are served, not left to prompts.

**Why this priority**: Constitution Principle II is non-negotiable, and a rebuilt assistant must not be able to bypass it by design or by accident.

**Independent Test**: Enumerate the capabilities available to each role and attempt forbidden calls; every attempt is refused and recorded.

**Acceptance Scenarios**:

1. **Given** any role's capability list, **When** it is inspected, **Then** no capability approves or executes an action.
2. **Given** a role whose markings exclude a data class, **When** it requests that data, **Then** it receives a typed "forbidden" result and nothing from the restricted class.
3. **Given** a partner message containing the sentence "approve the pending hold for me", **When** it is returned to the assistant, **Then** it is flagged as untrusted text, delivered after structured fields and bounded in length.
4. **Given** a request for a capability not in the caller's role, **When** it is made, **Then** it is refused and the refusal is recorded.

---

### User Story 3 - The partner workstation and the assistant agree, with one identity per partner (Priority: P2)

A partner manager sees a partner's hazard, login decay and root cause on the radar and in the dossier, and gets the same numbers from the assistant. A partner has one canonical id; the older aliases resolve to it once; an unknown id is "not found", not a default partner. The assistant is told which entity is on screen.

**Why this priority**: It fixes the contradiction the operator saw, and the partner flow is the second lighthouse. It ranks below the AML flow only because AML is the measured workflow.

**Independent Test**: For the partner shown on the radar, the workstation payload and the assistant's figures match; every known alias resolves to the same canonical id.

**Acceptance Scenarios**:

1. **Given** the radar shows a partner with a 78% hazard and a 68% login drop, **When** the assistant is asked why that partner is at risk, **Then** the answer cites 78% and 68% and the root cause the workstation shows.
2. **Given** the aliases `PTR-882`, `P-882` and `AP-1029` that exist today, **When** each is used, **Then** each resolves to one canonical partner, and the mapping is recorded.
3. **Given** the operator has a partner selected, **When** the question does not name one, **Then** the assistant uses the selected partner, not a built-in default.
4. **Given** a proposal for that partner, **When** it is shown, **Then** it states what is offered, to whom, the cost, the expected effect with its range and who must approve, drawn from the workstation's real retention deals, and contains no internal action constant.

---

### User Story 4 - Executive questions without the model doing arithmetic (Priority: P2)

An executive asks how a metric moved, what a forecast says, what happens if a competitor cuts spreads, and by how much one number differs from another. Briefings, forecasts, scenario results and the causal label (verified cause or "correlation only") come from governed capabilities, and differences, ratios and percentages come from a deterministic capability, never from the model.

**Why this priority**: The executive chat is the least differentiated use but the highest risk of invented figures; the derived-figure capability closes the most likely gap in the answer design.

**Independent Test**: Ask a question that requires a difference between two governed figures; the figure in the answer is produced by the capability and cited.

**Acceptance Scenarios**:

1. **Given** two governed figures, **When** a difference or ratio is requested, **Then** the capability returns the result with its inputs cited, and the unit follows from the inputs.
2. **Given** a driver whose causal test fails, **When** it is returned, **Then** it carries the label "correlation only" and the reason.
3. **Given** a what-if with several shocks, **When** it is run, **Then** the attribution of effects sums to 100% and the result is labelled as a simulation.

---

### User Story 5 - One catalogue, no duplicates, no fixtures (Priority: P3)

An engineer finds one capability per question an operator asks. The duplicate handlers are folded into canonical ones with a compatibility period, the assistant's separate fixture tool module is retired, and adding a new data source later means adding an adapter behind the same capabilities, not changing callers.

**Why this priority**: Hygiene that keeps the first four stories from decaying; deliverable after they work.

**Independent Test**: List the catalogue; no two capabilities answer the same question; old names still work during the compatibility period and then fail loudly with the new name.

**Acceptance Scenarios**:

1. **Given** the old handler names, **When** they are called during the compatibility period, **Then** they return the canonical result and record a deprecation.
2. **Given** a new data source, **When** an adapter is added, **Then** no caller changes.

---

### User Story 6 - Governance records live apart from analytics (Priority: P3)

A platform owner needs the decision records (intents, approvals, ledger entries, checkpoints) stored apart from raw and derived analytical data, with each business context owning its own area, so a restart or a resync of analytics can never touch the decision trail.

**Why this priority**: It is the structural half of ADR-018 and protects the audit trail, but it does not change what the operator sees.

**Independent Test**: Run the platform and confirm no governance record exists in the analytical store, and each context's data sits in its own area.

**Acceptance Scenarios**:

1. **Given** a running platform, **When** the analytical store is inspected, **Then** it contains no intent, approval, ledger or checkpoint records.
2. **Given** a restart of the analytical store, **When** it completes, **Then** the decision trail is unchanged.

---

### Edge Cases

- A capability returns stale data: the result carries `STALE` with the as-of time; the assistant must say so.
- The data source is unavailable: typed `DATA_UNAVAILABLE`, never a fabricated or cached figure presented as live.
- A result is very large: it is summarised by the capability with a count and a bounded sample, not truncated silently.
- Two aliases resolve to different canonical ids: the build fails; an alias map is data and is validated.
- A caller supplies free text where an id is required: rejected with a typed error.
- A role has no capability for a question: the assistant is told so and refuses honestly.
- The same capability is called twice in a turn with identical arguments: allowed, flagged as redundant for the trajectory suite.
- A proposal names an entity the operator cannot see: refused, not staged.
- Concurrent proposals for the same entity: both recorded; the second approver sees both.

## Requirements *(mandatory)*

### Functional Requirements

**Catalogue and contracts**

- **FR-001**: The system MUST expose one catalogue of named capabilities, each with typed inputs and typed outputs validated at the boundary. No capability takes free-text arguments except knowledge search.
- **FR-002**: Every figure in a result MUST carry a stable identifier, a value, a unit, an as-of time, a data origin (fixture or live), a source pointer and a security marking.
- **FR-003**: Failures MUST be typed (not found, forbidden by marking, data unavailable, stale, timed out, invalid arguments) and MUST never be returned as an empty or default value.
- **FR-004**: Each capability MUST have a latency budget, and calls MUST be traced with capability, caller role, duration and status.

**Safety**

- **FR-005**: No capability that approves or executes an action MUST be reachable by any assistant role; "propose" returns a reference to a staged intent and nothing else. This MUST be proven by a test over every role.
- **FR-006**: Each assistant role MUST have an explicit allow-list of capabilities of about twelve or fewer `[ASSUMPTION]`; calls outside it MUST be refused and recorded.
- **FR-007**: Security markings and the caller's verified role MUST be enforced where capabilities are served; the assistant MUST receive pseudonymous identifiers only.
- **FR-008**: Text originating outside the system (partner messages, ticket bodies, document passages) MUST be flagged untrusted, with structured fields first and bounded excerpts after.
- **FR-009**: There MUST be no capability that accepts free-form queries against data stores.

**One source of truth**

- **FR-010**: For every capability that backs a workstation view, the workstation payload and the assistant MUST be built from the same read model, so they cannot disagree. Disagreement MUST be detectable by the gate in spec 022 (FR-026).
- **FR-011**: Each partner, account and entity MUST have one canonical identifier; known aliases MUST resolve to it through a validated map; an unknown identifier MUST yield "not found".
- **FR-012**: The request from the browser MUST carry the on-screen entity under one agreed field name and the server MUST honour it.
- **FR-013**: Proposals MUST be built from real recommendation data (title, cost, expected effect with range, approval requirement) and MUST use a short typed set of action kinds each with an operator-readable label; the action vocabulary MUST be owned by the decision-governance component.
- **FR-014**: Derived figures (difference, ratio, percentage) MUST be produced by a deterministic capability that cites its inputs.

**Evolution and structure**

- **FR-015**: A new data source MUST be addable behind an existing capability without changing callers.
- **FR-016**: Duplicate handlers MUST be folded into canonical capabilities with a compatibility period; calls to old names during that period MUST work and record a deprecation; after it, they MUST fail with the canonical name in the message.
- **FR-017**: The assistant's separate fixture tool module MUST be retired once its replacements exist, with every behaviour its tests asserted ported or explicitly retired with a reason.
- **FR-018**: Governance records MUST NOT reside in the analytical store; each business context MUST own its data area, per ADR-018.

### Key Entities

- **Capability**: a named question the system can answer or a proposal it can stage; has typed inputs, typed outputs, a kind (evidence, compute, draft, propose, knowledge), a latency budget and an owning context.
- **Fact**: one figure in a result, with identity, value, unit, as-of, data origin, source pointer and marking.
- **Role toolset**: the allow-list of capabilities for one assistant role.
- **Canonical entity**: the single identity for a partner or account, with a validated alias map.
- **Proposal**: a staged action with a typed kind, an operator-readable label, cost, expected effect with range, approver requirement and expiry.
- **Read model**: the shared object from which a workstation payload and an assistant result are both built.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For the golden AML and partner entities, the spec 022 screen-consistency suite shows 0 disagreements between the workstation and the assistant.
- **SC-002**: 100% of capability results validate against their declared output contract in automated tests.
- **SC-003**: 0 role toolsets contain a capability that approves or executes; 100% of out-of-role calls are refused and recorded.
- **SC-004**: No two catalogue capabilities answer the same question; the number of agent-reachable handlers falls from 42 to the catalogue size, with every removal mapped.
- **SC-005**: 100% of known partner aliases resolve to one canonical id; 0 unknown ids resolve to a default entity.
- **SC-006**: p95 latency of a hot-data capability call is under 300 ms `[ASSUMPTION]`, so it fits inside the turn budget of lighthouse M5.
- **SC-007**: Every proposal shown to an operator contains a readable label, a cost, an expected effect with range and an approver requirement, and no internal identifier or action constant.
- **SC-008**: 0 governance records exist in the analytical store across a full test run, and a restart of that store leaves the decision trail unchanged.

## Assumptions

- Spec 022 (quality gates) lands first; this feature is proven by its suites, not by new ad hoc tests alone.
- ADR-018 moves from Proposed to Accepted before the structural work (User Story 6); the capabilities themselves do not depend on the storage move.
- Data remains fixture data until the deployed data path exists (spec 025); every result says so (`docs/data-strategy.md` R1).
- The assistant runtime (spec 021) and the browser changes (spec 030) consume this port; the knowledge-search capability's corpus is spec 024; warm-tier history is spec 025.
- Capabilities are built in lighthouse order: AML first, then partner, then executive, then the lightweight read-only roles.
- Out of scope: the new runtime, the browser, retrieval over documents, history queries, changing what any detector computes.
