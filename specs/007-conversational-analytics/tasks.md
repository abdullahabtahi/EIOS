# Tasks: Conversational Analytics & Multi-Agent Reasoning Mesh (F06)

**Input**: Design documents from `/specs/007-conversational-analytics/`

**Prerequisites**: plan.md, spec.md, data-model.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Initialize the module `src/eios/conversation/__init__.py` and create `src/eios/conversation/specialists/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T002 [P] Implement `RouteDecision` and `EvidenceItem` schemas in `src/eios/conversation/models.py`
- [x] T003 [P] Implement `ConversationalTurn` and `BlackboardState` schemas in `src/eios/conversation/models.py`
- [x] T004 [P] Implement `ConversationQueryRequest` and `ConversationQueryResponse` schemas in `src/eios/conversation/models.py`
- [x] T005 Define the `BaseSpecialistAgent` protocol in `src/eios/conversation/specialists/base.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Executive Cross-Domain Inquiry & Supervisory Routing (Priority: P1) 🎯 MVP

**Goal**: An executive queries the operational cockpit in free-form natural language and is routed to a specialist (Synthesis, AML, Churn, Fraud) yielding a metric-audited response.

### Implementation for User Story 1

- [x] T006 [P] [US1] Implement `SynthesisSpecialist` with OMCP tool allow-list in `src/eios/conversation/specialists/synthesis.py`
- [x] T007 [P] [US1] Implement `SentinelAMLSpecialist` with OMCP tool allow-list in `src/eios/conversation/specialists/aml.py`
- [x] T008 [P] [US1] Implement `ChurnRadarSpecialist` in `src/eios/conversation/specialists/churn.py`
- [x] T009 [P] [US1] Implement `PartnerFraudSpecialist` in `src/eios/conversation/specialists/fraud.py`
- [x] T010 [US1] Refine the LangGraph Supervisor node logic in `src/eios/conversation/graph.py` to route based on query intent (targeting $\ge 95\%$ accuracy).
- [x] T011 [US1] Implement the MetricAuditorGate egress scanner logic inside `src/eios/conversation/auditor_bridge.py` ensuring zero untraceable numbers.
- [x] T012 [US1] Connect `auditor_bridge.py` to the egress node in `src/eios/conversation/graph.py`.
- [x] T013 [US1] Implement the facade `ConversationEngine` in `src/eios/conversation/engine.py` to invoke the `StateGraph`.

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Multi-Turn Conversational Drill-Down & Session Memory (Priority: P2)

**Goal**: Executive asks sequential follow-up questions drilling down into entities without repeating background context.

### Implementation for User Story 2

- [x] T014 [US2] Implement sliding-window context compactor in `src/eios/conversation/memory.py`
- [x] T015 [US2] Implement pronominal entity resolution logic in `src/eios/conversation/memory.py` to anchor entities across turns.
- [x] T016 [US2] Integrate `memory.py` into the LangGraph state in `src/eios/conversation/graph.py` to preserve historical evidence ledger.

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently.

---

## Phase 5: User Story 3 - Assumption Stress-Testing & Counterfactual Exploration (Priority: P2)

**Goal**: Executive challenges assumptions (e.g., "What if..."), invoking causal simulation engines and bounding confidence intervals.

### Implementation for User Story 3

- [x] T017 [US3] Add counterfactual detection logic inside the Synthesis Specialist in `src/eios/conversation/specialists/synthesis.py`.
- [x] T018 [US3] Integrate the causal `run_scenario` and `get_forecast` OMCP tools into `synthesis.py` to execute parametric shocks.
- [x] T019 [US3] Add extrapolation warning logic (for shocks $> 3.0\sigma$) inside the Synthesis response generation.

**Checkpoint**: All user stories up to P2 should now be functional.

---

## Phase 6: User Story 4 - Honest Uncertainty & Speculative Query Refusal (Priority: P3)

**Goal**: System identifies speculative queries with no grounding data and gracefully refuses using the canonical phrase "insufficient data".

### Implementation for User Story 4

- [x] T020 [US4] Add data-availability bounds check to the Supervisory Router node in `src/eios/conversation/graph.py`.
- [x] T021 [US4] Ensure `RouteDecision` enforces `refusal_required=True` when necessary.
- [x] T022 [US4] Implement short-circuit refusal logic in `src/eios/conversation/engine.py` that bypasses specialists and returns the refusal template.

---

## Phase 7: User Story 5 - Governed Action Proposal Staging from Dialogue (Priority: P3)

**Goal**: System intercepts operational requests and stages them as non-autonomous `RecommendationCard` proposals.

### Implementation for User Story 5

- [x] T023 [US5] Complete the `ActionExecutionSink` logic in `src/eios/conversation/graph.py` to capture intercepted operational tools and convert them to `RecommendationCard`.
- [x] T024 [US5] Implement statutory compliance arbitration in the Supervisor node (`graph.py`) to block commercial actions if AML alerts exist.
- [x] T025 [US5] Integrate staged actions into the `ConversationQueryResponse` returned by `src/eios/conversation/engine.py`.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T026 Code cleanup and refactoring across `src/eios/conversation/`
- [x] T027 Performance optimization to ensure $p95 < 3.5\text{s}$ turn latency (timeout constraints and parallel tool execution)
- [x] T028 Validate against all 10 canonical golden dialogues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion. They can proceed sequentially in priority order (P1 → P2 → P3).

### Parallel Opportunities

- All schemas and data models in Phase 2 can be defined concurrently.
- All 4 specialist agents in Phase 3 (Synthesis, AML, Churn, Fraud) can be implemented in parallel.
