# Tasks: Institutional Cockpit Ergonomics, Sovereign Light & Tripartite Synchronization (017-cockpit-ergonomics-polish)

**Input**: Design documents from `/specs/017-cockpit-ergonomics-polish/` (spec.md, plan.md)  
**Prerequisites**: spec.md, plan.md  
**Status**: In Progress

---

## Phase 1: Setup & Foundational

- [ ] T001 Update `.specify/feature.json` to feature `specs/017-cockpit-ergonomics-polish` and add custom scrollbar utilities in `FEIOS/web-prototype/src/app/globals.css`.

---

## Phase 2: User Story 1 - Spatial Fluidity & Responsive Ergonomics (Priority: P1) 🎯 MVP

- [ ] T002 Update `tripartite-shell.tsx` with fluid panel allocations (`w-72 2xl:w-80` rail, `w-[440px] xl:w-[480px] 2xl:w-[540px]` dossier, `flex-1 min-w-[460px]` canvas) and universal collapse chevrons (`lg:flex`).
- [ ] T003 Update `kinetic-canvas.tsx` with single-line sub-headers and auto-fit responsive grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`) to eliminate text-wrapping and telemetry card truncation on viewports $\le 1366\text{px}$.

---

## Phase 3: User Story 2 - 100% Palantir Sovereign Light Shell Chrome (Priority: P1) 🎯 MVP

- [ ] T004 Recolor `HeaderNav` in `header-nav.tsx` into pure Sovereign Light mode (`#ffffff` surface, `1px solid #e2e8f0` border, `#0f172a` typography, light latency telemetry pill, and deep cobalt active tab underline).
- [ ] T005 Recolor `GovernedActionShelf` in `governed-action-shelf.tsx` into pure Sovereign Light mode (`#ffffff` elevated tray, `#e2e8f0` dividers, `#0f172a` text, clean light Two-Phase Commit cards, and `#0d8050` verified signatures).

---

## Phase 4: User Story 3 - Coordinated Tripartite State Synchronization (Priority: P2)

- [ ] T006 Enhance `cockpit-context.tsx` and state reducer so `selectTriageItem` synchronizes the active entity ID across center dossier and right kinetic canvas focus state.
- [ ] T007 Update `copilot-dossier.tsx` and `kinetic-canvas.tsx` to react immediately to the synchronized triage entity selection.

---

## Phase 5: User Story 4 - What-If Baseline Affordances & Keyboard-First Navigation (Priority: P2)

- [ ] T008 Add "Reset to Baseline (0 bps)" snap button and preset chips (`-25 bps`, `0 bps`, `+25 bps`) to `what-if-slider.tsx`.
- [ ] T009 Create `keyboard-shortcuts-modal.tsx` with institutional styling and wire global keyboard event listeners (`[`, `]`, `?`) in `tripartite-shell.tsx` and `header-nav.tsx`.

---

## Phase 6: User Story 5 - Craft-Floor Browser Surfaces & Polish (Priority: P3)

- [ ] T010 Apply `tabular-nums` on figures, `scrollbar-thin` on dossier scroll containers, and verify WCAG 2.2 AA focus rings (`focus-visible:ring-2 focus-visible:ring-[#106ba3]`).

---

## Phase 7: Automated Testing, Browser Verification & Impeccable Re-Assessment

- [ ] T011 Run frontend test suite (`bun run test`) and update component test assertions for new classes and controls.
- [ ] T012 Run TypeScript compiler (`bun x tsc --noEmit`) and backend test suite (`pytest tests/cockpit/ -v`).
- [ ] T013 Live browser verification via Chrome DevTools MCP at 1920x1080 and 1280x800, capturing screenshots.
- [ ] T014 Run `impeccable detect` and record the re-assessed critique score.
