# Feature Specification: Assistant Runtime

**Feature Branch**: `021-adk-agent-runtime`

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "Replace the current conversational agent (a hand-written tool loop plus a keyword-routed multi-agent mesh) with one production runtime for the workstation assistants: it knows who is asking, keeps the conversation, answers only with figures it can prove, proposes actions through governance, degrades honestly, and is judged by the same gates as the agent it replaces."

**Context**: `docs/adk-research.md` (decisions A-2 to A-10, pre-mortem), `docs/agent-architecture.md` (sections 2, 3 and 9), `docs/adk.md` (defect register B1 to B12), `specs/022-agent-quality-gates` (the gates and the baseline), `specs/023-governed-tool-port` (the tools it uses). The choice of runtime framework is recorded in a new ADR that supersedes ADR-016; it is not a requirement of this specification.

## Why this exists

The current assistant has twelve recorded defects. It shares one session across all operators and takes the operator's role from the request body (B1, B3). It never learns which entity is on screen (B2). It forgets earlier turns (B4). It routes by keywords and answers some questions from hard-coded branches with fixed entity ids (B5, B6). It calls fixture tools that bypass governance (B7). Its number checker lets wrong figures through and blocks right ones (when probed it let all 5 wrong figures through and blocked both faithful answers). A turn can take up to about a minute `[ASSUMPTION]` because wrong figures trigger repeated correction rounds. Its session store is lost on restart (B9). The multi-agent mesh is a stub (B12).

This feature replaces it with one runtime whose answers are built so that an unsupported figure cannot appear, whose identity and memory come from the verified operator, and whose behaviour is judged by the gates in spec 022. It does not change what any detector or engine computes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A grounded answer an investigator can trust (Priority: P1)

An AML investigator looks at an alert and asks the assistant about the account on screen. The answer is in plain language, every figure in it is filled in from a governed result and states its unit and as-of time, the sources are one click away, and it says when the data is demo data. If the data needed is missing, it says so and states no figure.

**Why this priority**: This is the lighthouse workflow (`docs/lighthouse.md`) and the reason for the rebuild. Faithfulness (M3) is a release blocker.

**Independent Test**: Run the spec 022 faithfulness and trajectory suites against the new runtime on the AML golden cases. Delivers value alone: one workstation with a trustworthy assistant.

**Acceptance Scenarios**:

1. **Given** an account with a 16x discrepancy on screen, **When** the investigator asks what the discrepancy is, **Then** the answer states 16x and cites the result it came from, and the faithfulness gate passes.
2. **Given** a question that needs a figure no capability returns, **When** asked, **Then** the answer says the data is unavailable and contains no figure.
3. **Given** the model drafts an answer containing a figure that is not backed by a result, **When** the answer is assembled, **Then** the figure is never shown; the assembly fails closed with a plain explanation after at most three attempts.
4. **Given** the data is demo data, **When** the answer is shown, **Then** it says so once, not on every figure.

---

### User Story 2 - It knows who is asking and keeps the conversation (Priority: P1)

An operator's role and identity come from their verified sign-in, never from the request. Each operator has their own conversation per entity, which survives a refresh and a service restart, and follow-up questions ("and their login decay?") resolve to the entity already under discussion. One operator can never see another's conversation.

**Why this priority**: It fixes defects B1 to B4 and B9 and is a precondition for four-eyes governance to mean anything.

**Independent Test**: Two operators converse about the same entity; neither sees the other's turns; a restart keeps both threads; changing the role in the request body changes nothing.

**Acceptance Scenarios**:

1. **Given** two signed-in operators, **When** both ask about the same partner, **Then** each has a separate thread and neither can retrieve the other's.
2. **Given** a request that claims a different role than the signed-in one, **When** it is processed, **Then** the verified role is used.
3. **Given** a conversation in progress, **When** the service restarts, **Then** the operator resumes the same thread.
4. **Given** the previous turn was about partner X, **When** the operator asks "why is it at risk?", **Then** the answer is about partner X.

---

### User Story 3 - An assistant per workstation (Priority: P2)

Each of the five workstations (executive, AML investigator, partner manager, compliance auditor, data operations) gets an assistant with the tools and instructions of that job and nothing else. The right one is chosen from the verified role and workstation, not guessed from keywords. The executive assistant can synthesise across domains using the governed synthesis capabilities.

**Why this priority**: It delivers the product's breadth after the lighthouse works. Smaller toolsets also select tools more reliably.

**Independent Test**: For each role, the trajectory suite passes on its golden cases and an out-of-role request is refused.

**Acceptance Scenarios**:

1. **Given** a partner manager signed in, **When** they ask an AML-only question, **Then** the assistant says that is outside this workstation and offers no AML data.
2. **Given** an executive asking why a metric moved, **When** answered, **Then** it uses governed metric, causal and forecast capabilities and labels correlation as correlation.

---

### User Story 4 - Proposals go through governance (Priority: P2)

When the assistant recommends an action, it proposes it. The proposal reads in plain terms (what, to whom, how much, expected effect with range, who must approve) and appears in the approvals area as a real pending item created by the decision-governance component. The assistant never approves or executes, and the browser's approve and reject controls act on the real record, not on local state.

**Why this priority**: Constitution Principle II is non-negotiable, and today's browser controls are client-side only (A5).

**Independent Test**: Ask the assistant to hold a withdrawal; a pending item exists in the governance record; the same operator cannot approve it; a second operator can.

**Acceptance Scenarios**:

1. **Given** a recommendation to hold a withdrawal, **When** proposed, **Then** a pending approval exists with a readable label, an expiry and the evidence it was based on.
2. **Given** the operator who proposed it, **When** they try to approve it, **Then** it is refused.
3. **Given** a request to "just approve it for me", **When** received, **Then** the assistant declines and points to the approvals area.

---

### User Story 5 - Honest when things fail (Priority: P2)

If the language model, a data source or a safety service is unavailable, the operator sees a plainly labelled saved answer with the time and reason, or a clear "I can't answer that right now", never an invented answer. Turn time is bounded.

**Why this priority**: Constitution Principle VIII and a precondition for an operator ever trusting a slow tool.

**Independent Test**: Disable each dependency in turn; the response is labelled, carries a reason and contains no figure that was not previously verified.

**Acceptance Scenarios**:

1. **Given** the model is unavailable, **When** the operator asks a question with a saved answer, **Then** the saved answer is shown with its time and a reason.
2. **Given** no saved answer exists, **When** the model is unavailable, **Then** the assistant says it cannot answer now and offers no figure.
3. **Given** a turn running longer than its limit, **When** it expires, **Then** the operator is told and the turn is recorded as inconclusive.

---

### User Story 6 - Protected at the edges (Priority: P3)

What the operator types, what the model says, and what comes back from tools (including partner messages and document text) is screened for attempts to hijack or leak. A failed screening blocks the turn and says so; an unavailable screening service blocks rather than letting content through unscreened.

**Why this priority**: Defence in depth on top of the structural protections of spec 023; the built-in screening of the chosen framework does not cover tool results, so this story closes that gap.

**Independent Test**: The spec 022 adversarial suite, including paraphrased attacks and injection through tool text, reports 0 successful attacks.

**Acceptance Scenarios**:

1. **Given** a tool result that contains an instruction, **When** it reaches the assistant, **Then** it is screened and treated as data, and no action follows from it.
2. **Given** the screening service is unavailable, **When** a turn arrives, **Then** it is blocked with a clear message.

---

### User Story 7 - One assistant, the old one retired (Priority: P3)

When the new runtime passes the same gates as the old one and the behaviours the existing conversation tests assert are ported or deliberately retired, the old tool loop, keyword routers, regex checker and the stub mesh are removed.

**Why this priority**: A flag day is avoided, but two assistants must not live on.

**Independent Test**: The old modules are absent; every previously asserted behaviour is either passing on the new runtime or listed as retired with a reason.

**Acceptance Scenarios**:

1. **Given** the gates pass on the new runtime, **When** the old code is removed, **Then** the full test suite still passes.
2. **Given** a behaviour asserted only by an old test, **When** it is retired, **Then** the reason is recorded.

---

### Edge Cases

- A question that spans two workstations' domains.
- A follow-up with no entity in the thread and none on screen: the assistant asks which one.
- The operator switches entity mid-thread: the thread follows the new entity.
- Two quick questions in a row from the same operator.
- The model returns malformed or empty output.
- A tool is slow while others finish.
- The same answer needs more than one source of the same fact that differ: it says so rather than choosing silently.
- An operator without the marking for a requested data class asks about it.
- A very long conversation exceeds what the model can read.
- Demo data and live data in one answer.

## Requirements *(mandatory)*

### Functional Requirements

**Answers**

- **FR-001**: The assistant MUST produce answers in which every figure is inserted by the system from a governed result, and MUST NOT display any figure the model typed itself.
- **FR-002**: An answer MUST state each figure's unit and as-of time, MUST identify demo data once per answer, and MUST make each figure's source reachable.
- **FR-003**: If an answer cannot be assembled faithfully within three attempts, the assistant MUST fail closed with a plain explanation and no figure.
- **FR-004**: The answer MUST be a structured result containing the text, figure references, citations, proposed actions, view commands for the workstation (not acted on by this feature), the data origin, and replay and block indicators.
- **FR-005**: The assistant MUST report progress as real steps (which capability it is using), not a generic wait indicator.

**Identity and memory**

- **FR-006**: Role and operator identity MUST come from the verified sign-in; values in the request body MUST be ignored for access decisions.
- **FR-007**: Conversations MUST be stored per operator and entity, MUST survive restarts, and MUST be inaccessible to other operators.
- **FR-008**: The assistant MUST receive the on-screen entity and resolve follow-up references against the thread.

**Workstation assistants**

- **FR-009**: Each of the five workstations MUST have its own assistant with its own role toolset from spec 023, selected from the verified role and workstation.
- **FR-010**: Requests outside a role's domain MUST be declined and recorded.

**Governance**

- **FR-011**: The assistant MUST NOT approve or execute any action; proposals MUST create real pending records through the decision-governance component, with a readable label, expiry and evidence.
- **FR-012**: The browser's approve, reject and stage controls MUST act on those real records.
- **FR-013**: Compliance-hold arbitration and the three-cycle bound on self-correction MUST be preserved as deterministic behaviour, not prompt instructions.

**Failure and safety**

- **FR-014**: On model, data or safety-service failure the assistant MUST show a labelled saved answer with time and reason, or state that it cannot answer; it MUST NOT invent content. A saved answer MUST set the replay indicator and a reason.
- **FR-015**: User input, model output and tool results MUST be screened; an unavailable screening service MUST block the turn.
- **FR-016**: Every turn MUST have a time limit; an expired turn is reported and recorded as inconclusive.

**Operations**

- **FR-017**: The assistant MUST run inside the existing API service and MUST read the model name and settings from configuration, never from source.
- **FR-018**: Every turn MUST emit the telemetry record defined in spec 022.
- **FR-019**: The new runtime MUST pass the spec 022 gates (faithfulness, trajectory, safety, screen consistency) before the old one is removed.
- **FR-020**: The old tool loop, keyword routers, regex number checker and stub mesh MUST be removed only after parity, and every behaviour their tests assert MUST be ported or retired with a recorded reason.

### Key Entities

- **Assistant turn**: one question and answer, with its identity, entity context, capabilities used, figures and their sources, and outcome.
- **Conversation**: the thread for one operator and one entity, durable, private to the operator.
- **Answer**: the structured result defined in FR-004.
- **Figure reference**: a placeholder in the draft text that the system resolves to a governed result.
- **Proposal**: a pending action created through governance, from spec 023.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the golden cases, 100% of figures shown to operators resolve to a governed result (lighthouse M3, a release blocker).
- **SC-002**: The adversarial suite shows 0 successful attacks across all families, including paraphrased and tool-text injection.
- **SC-003**: Turn time p95 is under 15 seconds `[TARGET]` (lighthouse M5), measured against the baseline from spec 022 taken before this feature.
- **SC-004**: 0 cross-operator conversation leaks in tests; 100% of threads survive a restart.
- **SC-005**: 100% of proposals appear as real pending approvals; 0 can be approved by their proposer.
- **SC-006**: With each dependency disabled in turn, 100% of responses are labelled and 0 contain an unverified figure.
- **SC-007**: Trajectory pass rate on the golden cases is at or above the baseline from spec 022 by a margin set before the first run, and no workstation is below it `[ASSUMPTION]`.
- **SC-008**: Every behaviour asserted by the existing conversation tests is ported or retired with a reason, and the full suite passes after the old code is removed.

## Assumptions

- Spec 022 provides the baseline and gates first; spec 023 provides the typed capabilities. Without a measured baseline, no improvement is claimed.
- The runtime framework is Google's Agent Development Kit, adopted through a new ADR superseding ADR-016; the model reaches the runtime only through the existing provider boundary; the ADK is embedded in the existing API service on Cloud Run (decision A-3), not deployed as its own service in this feature.
- Knowledge retrieval over regulations is spec 024; history queries on the warm tier are spec 025; the browser chat view is spec 030; registration in an enterprise assistant catalogue is spec 028.
- Until the deployed data path exists (spec 025), answers are about fixture data and say so.
- Out of scope: new detectors, new metrics, the browser redesign, long-term memory across conversations (a privacy decision deferred), and overnight pre-assembled dossiers (spec 029, deferred).
