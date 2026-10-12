# Feature Specification: Institutional Cockpit Ergonomics, Sovereign Light & Tripartite Synchronization (017-cockpit-ergonomics-polish)

**Feature Branch**: `017-cockpit-ergonomics-polish`  
**Created**: 2026-10-10  
**Status**: Ratified  
**Authoritative References**: `DESIGN.md`, `specs/016-cockpit-frontend/spec.md`, `.specify/memory/constitution.md` (Principles I–VIII), `reference/craft-floor.md`, Impeccable Critique `2026-10-10T08-48-57Z__feios-web-prototype-src-app-cockpit-page-tsx.md`  
**Input**: User directive: "what's next to make this truly an apple award winning financial web application? implement with spec driven development approach"

---

## 1. System Vision & Objective

Transform the FEIOS Common Operational Picture (COP) into an award-winning institutional financial workstation combining Palantir Foundry / QuantumBlack rigor with Apple-caliber spatial fluidity and ergonomic craft. Address the key UX/UI deficiencies identified in the design critique:
1. Eliminate the 1280px viewport squeeze and enable universal panel collapse.
2. Unify the shell into 100% Palantir Sovereign Light Mode, eliminating the dark slate header/footer "sandwich".
3. Synchronize triage alert selection across Left Rail, Center Dossier, and Right Kinetic Canvas.
4. Provide tactile What-If simulation controls (snap-to-baseline, preset chips) and global keyboard navigation.
5. Elevate browser surfaces with themed scrollbars, tabular figures, and WCAG 2.2 AA focus rings.

---

## 2. User Scenarios & Testing (Mandatory)

### User Story 1 - Spatial Fluidity & Responsive Ergonomics (Priority: P1) 🎯 MVP

As an **Institutional Risk Operator or Quant Analyst** viewing the cockpit on any display (from a 13" MacBook at $1280 \times 800$ to an ultra-wide $3840 \times 2160$ monitor),  
I want fluid flex panel allocations and accessible collapse controls,  
So that the Right Kinetic Canvas never cramps, titles never wrap into three jagged lines, and metric cards display without text truncation.

**Why this priority**: The canvas is where relational collusion rings, causal DAGs, and quadrant scatter models are explored. Cramping the canvas destroys analytical utility on laptop displays.

**Independent Test**: Load `http://localhost:3000/cockpit` at $1280 \times 800$; verify the Kinetic Canvas maintains $\ge 460\text{px}$ width; verify the canvas header stays on a single line; verify telemetry cards do not truncate; verify clicking the collapse chevrons (`<` and `>`) smoothly folds panels on all screens $\ge 1024\text{px}$.

**Acceptance Scenarios**:
1. **Given** a $1280 \times 800$ viewport, **When** the page renders, **Then** panel widths adapt fluidly (`w-72` rail, `w-[440px]` dossier, `flex-1 min-w-[460px]` canvas) without horizontal page overflow.
2. **Given** any desktop viewport $\ge 1024\text{px}$, **When** the operator clicks the collapse chevron on the Left Rail or Right Canvas, **Then** the panel collapses to a 32px slim rail with vertical label, and expands back on click.
3. **Given** the Partner Manager or Data Operations views at 1280px, **When** inspecting the sub-header and cards, **Then** the title renders cleanly on one line and telemetry badges fit within container bounds.

---

### User Story 2 - 100% Palantir Sovereign Light Shell Chrome (Priority: P1) 🎯 MVP

As an **Executive or Compliance Officer**,  
I want the Top Header Bar and Bottom Governed Action Shelf to adhere strictly to the Sovereign Light specification in `DESIGN.md`,  
So that the interface has cohesive editorial materiality without high-contrast visual jarring between dark chrome and light content cards.

**Why this priority**: High-contrast "dark sandwiches" cause eye strain and violate the strict 100% light-mode design mandate.

**Independent Test**: Visually inspect the top header and bottom shelf in Chrome DevTools; verify `#ffffff` background with 1px `#e2e8f0` structural borders, `#0f172a` primary text, `#106ba3` active states, and `#0d8050` / `#a82a2a` semantic badges.

**Acceptance Scenarios**:
1. **Given** the Header Navigation bar, **When** rendered, **Then** its background is `#ffffff` with a `1px solid #e2e8f0` bottom border, dark slate typography, clean light-mode latency pills, and cobalt active role indicators.
2. **Given** the Governed Action Shelf, **When** collapsed or expanded, **Then** its container background is `#ffffff` with subtle elevation and border `#cbd5e1`, maintaining Two-Phase Commit prominence without dark slate backgrounds.
3. **Given** the action cards inside the shelf, **When** inspected, **Then** cards render on `#ffffff` with `#0f172a` titles, Cloud KMS P-256 verification badges, and high-contrast authorization buttons.

---

### User Story 3 - Coordinated Tripartite State Synchronization (Priority: P2)

As an **AML Investigator or Partner Manager**,  
I want selecting an alert in the Left Triage Rail to immediately update both the Center Dossier and focus the corresponding node on the Right Kinetic Canvas,  
So that I don't have to hold multiple disconnected entity IDs in working memory.

**Why this priority**: Eliminates Cowan's working-memory violations and prevents operator disorientation during multi-entity triage.

**Independent Test**: Click `Partner AP-1029` in the Triage Rail; verify the Center Dossier displays `Entity AP-1029` and the Right Canvas scatter inspector focuses on `AP-1029` rather than defaulting to `PTR-882`. Click `AML Alert CR84920`; verify the topological graph highlights `CR84920`.

**Acceptance Scenarios**:
1. **Given** the Partner Manager workstation, **When** the operator clicks `Partner AP-1029` in the Triage Rail, **Then** both the center dossier and right canvas scatter inspector update to entity `AP-1029`.
2. **Given** the AML Investigator workstation, **When** the operator clicks `AML Alert CR84920`, **Then** the topological network graph centers on node `CR84920` with collusion edges highlighted.

---

### User Story 4 - What-If Baseline Affordances & Keyboard-First Navigation (Priority: P2)

As a **Senior Quant Trader or Executive**,  
I want tactile What-If simulation slider affordances and global keyboard shortcuts,  
So that I can execute rapid sensitivity analysis and navigate the cockpit without reaching for the mouse.

**Why this priority**: Power users require rapid baseline resets and keyboard accelerators for high-velocity operational decisions.

**Independent Test**: Drag the spread slider to $+35\text{ bps}$; click "Reset to Baseline (0 bps)"; verify the slider and causal DAG immediately snap back to $0\text{ bps}$ baseline. Press `[` to toggle rail; press `]` to toggle canvas; press `?` to open the Keyboard Shortcuts modal.

**Acceptance Scenarios**:
1. **Given** the What-If simulation slider, **When** dragging the value away from 0, **Then** a visible "Reset to Baseline (0 bps)" button and quick-snap chips (`-25 bps`, `0 bps`, `+25 bps`) appear and function with single-click precision.
2. **Given** the cockpit active in browser, **When** pressing `[` or `]`, **Then** the left rail and right canvas toggle collapsed/expanded states.
3. **Given** the cockpit active in browser, **When** pressing `?`, **Then** a sleek modal opens detailing all operational shortcuts.

---

### User Story 5 - Craft-Floor Browser Surfaces & Tabular Typography (Priority: P3)

As an **Operator reviewing dense financial figures**,  
I want tabular numbers, themed slim scrollbars, and WCAG 2.2 AA compliant focus rings,  
So that the UI feels finished to Apple award-winning standards.

**Why this priority**: Browser default scrollbars and fluctuating non-tabular digits create layout jitter and undermine aesthetic trust.

**Independent Test**: Verify `tabular-nums` is applied to all currencies and latencies; verify custom slim scrollbars on dossiers; verify visible focus rings when navigating via `Tab`.

**Acceptance Scenarios**:
1. **Given** streaming numbers, **When** digits update, **Then** column widths remain rock-solid with zero layout shift.
2. **Given** scrollable panels, **When** scrolling, **Then** the scrollbar renders as a sleek 4px slate pill (`scrollbar-thin`).
3. **Given** keyboard navigation, **When** tabbing between controls, **Then** an unambiguous `ring-2 ring-[#106ba3]` focus ring is displayed.

---

## 3. Non-Functional Requirements & Invariants

1. **Light Mode Invariant**: 100% Palantir Sovereign Light mode; zero dark mode toggles or regressions.
2. **Contrast Invariant**: WCAG 2.2 AA contrast compliance ($\ge 4.5:1$ text, $\ge 3:1$ UI controls).
3. **Performance SLA**: Panel collapse/expand transitions complete within 200ms without layout thrashing.
4. **Test Suite Integrity**: All existing 19 frontend Vitest tests and 58 backend pytest tests must pass without regressions.
