# Tasks: Production-Grade Partner Churn & Retention Intelligence Hardening

**Input**: Design documents from `/specs/020-production-partner-intelligence/` (`spec.md`, `plan.md`, `data-model.md`)

**Prerequisites**: `spec.md` (required), `plan.md` (required), `data-model.md`

**Organization**: Tasks are grouped by user story to enable independent implementation, testing, and MVP delivery.

---

## Phase 1: Foundational Prerequisites (Shared Infrastructure)

**Purpose**: Core schema and API foundations that all user stories depend on.

- [x] T001 [P] Sanitize legacy vendor references and expose extended `PartnerChurnItem` fields with historical drift vectors in `FEIOS/src/eios/api/routes_churn.py`.
- [x] T002 [P] Update TypeScript interfaces in `FEIOS/web-prototype/src/components/cockpit/state/cockpit-types.ts` for extended historical drift, causal refutation responses, and cohort batch actions.

---

## Phase 2: User Story 1 - Synchronized Dual Scatter-Triage Grid & Portfolio Scale (Priority: P1) 🎯 MVP

**Goal**: Provide a sortable, searchable portfolio grid synchronized with the Churn Hazard Radar, enabling high-volume partner triage.

- [x] T003 [P] [US1] Create high-density, sortable `PartnerTriageGrid` component in `FEIOS/web-prototype/src/components/cockpit/common/partner-triage-grid.tsx` with sorting by VaR, $P(\text{churn})$, Days to Churn, and quick text search.
- [x] T004 [US1] Integrate `PartnerTriageGrid` into `FEIOS/web-prototype/src/components/cockpit/common/churn-radar-scatter.tsx` and `partner-workstation.tsx`, bi-directionally synchronizing node selection and quadrant filtering with `cockpit-context.tsx`.
- [x] T005 [P] [US1] Expand monitored partner dataset to 20+ realistic international records across LatAm, SEA, and Europe in backend service `FEIOS/src/eios/cockpit/partner.py` and wire `api-bridge.ts` (`fetchChurnRadar()` & SSE stream) into `churn-radar-scatter.tsx` and `partner-triage-grid.tsx` with offline fallback.

---

## Phase 3: User Story 2 - 30D/90D Historical Decay Trajectories & Change-Point Breadcrumbs (Priority: P1)

**Goal**: Render temporal drift vectors and velocity sparklines on the radar canvas so operators can see where at-risk partners originated.

- [x] T006 [US2] Implement SVG dotted historical drift trails with directional velocity chevrons ($T-30\text{d}$, $T-14\text{d}$, $T-0\text{d}$) on the Cartesian grid in `FEIOS/web-prototype/src/components/cockpit/common/churn-radar-scatter.tsx`.
- [x] T007 [US2] Add 30-day velocity sparklines in the Diagnostic Inspector displaying daily login drop and turnover velocity trends.

---

## Phase 4: User Story 3 - Live Backend Causal SCM Refutation & What-If Concession API (Priority: P2)

**Goal**: Connect the What-If retention simulator to the live backend DoWhy SCM causal inference endpoint.

- [x] T008 [US3] Wire the What-If concession range slider to dispatch debounced ($250\text{ms}$) requests to `POST /api/v1/churn/partner/{id}/what-if` via `FEIOS/web-prototype/src/components/cockpit/state/api-bridge.ts`.
- [x] T009 [US3] Render DoWhy refuter Placebo test $p$-values, confidence intervals ($+74\% \pm 8\%$), and Gemini 3.8 Flash causal rationale in the Diagnostic Inspector.

---

## Phase 5: User Story 4 - Driver-Adaptive Action Playbooks & 1-Click Cohort Batch Remediation (Priority: P2)

**Goal**: Adapt retention playbooks to the diagnosed root cause and allow 1-click batch remediation for regional cohorts.

- [x] T010 [US4] Implement driver-adaptive action playbooks in the Diagnostic Inspector (VIP Cashier Rail for latency, Spread Match Concession for poaching, Rebate Reconciliation for disputes).
- [x] T011 [US4] Add 1-click batch cohort remediation button in `COHORTS` mode in `churn-radar-scatter.tsx`, staging multi-target Two-Phase Commit proposals with Cloud KMS P-256 nonces.

---

## Phase 6: User Story 5 - Closed-Loop Experience Library & Active Learning Calibration (Priority: P3)

**Goal**: Surface empirical outcome win rates and live shadow model Brier calibration metrics.

- [x] T012 [US5] Surface historical playbook win-rate ratios (e.g., 78.5% retention across 14 historical deals) and live Brier calibration score ($0.082$) in `churn-radar-scatter.tsx`.

---

## Phase 7: Automated Verification & Test Hardening

**Goal**: Guarantee 100% test pass rate and zero TypeScript compiler errors.

- [x] T013 [US1..US5] Update Vitest suite `FEIOS/web-prototype/src/tests/cockpit/partner-workstation.test.tsx` verifying grid search, scatter-table synchronization, and batch cohort staging.
- [x] T014 Execute full test suite (`npx vitest run`) and type checking (`npx tsc --noEmit`) to ensure zero regressions.

---

## Dependencies & Execution Strategy

```
Phase 1: Foundations (T001, T002)
   │
   ├──► Phase 2: US1 Dual Scatter-Grid (T003, T004, T005) [MVP]
   │       │
   │       └──► Phase 3: US2 Historical Drift (T006, T007)
   │
   ├──► Phase 4: US3 Backend Causal What-If (T008, T009)
   │
   ├──► Phase 5: US4 Driver-Adaptive & Cohort Remediation (T010, T011)
   │
   └──► Phase 6: US5 Closed-Loop Outcomes (T012)
           │
           └──► Phase 7: Verification & Testing (T013, T014)
```
