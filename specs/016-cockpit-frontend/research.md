# Research & Architectural Decisions: Institutional Operator Cockpit (016-cockpit-frontend)

**Branch**: `016-cockpit-frontend` | **Date**: 2026-10-10 | **Feature Spec**: [spec.md](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/specs/016-cockpit-frontend/spec.md)

This document records the architectural research and technical decisions for Feature `016-cockpit-frontend` (Institutional Operator Cockpit & QuantumBlack Design System Frontend), grounded in live queries executed against the **Context7 MCP** for Next.js 16, React 19, Tailwind CSS v4, and Radix UI Primitives.

---

## 1. Context7 MCP Documentation Ingestion Summary

During Phase 0, Context7 MCP was queried across key UI library components:
1. **Next.js 16 App Router** (`/vercel/next.js`):
   - Retrieved client component patterns, layout hydration boundaries (`'use client'`), typed navigation, dynamic route handlers, and shared state propagation across nested workstation panels.
2. **Tailwind CSS v4** (`/tailwindlabs/tailwindcss.com`):
   - Retrieved v4 `@theme` directive mechanics, CSS custom property mapping, OKLCH and hex color tokens, custom typography tracking scales, and clean removal of legacy `tailwind.config.js` in favor of stylesheet-native tokens.
3. **Radix UI Primitives** (`/websites/radix-ui_primitives`):
   - Retrieved accessible anatomy for `Popover` (`Root`, `Trigger`, `Portal`, `Content`, `Arrow`) for deterministic metric provenance popovers and `Dialog` (`Root`, `Trigger`, `Portal`, `Overlay`, `Content`, `Title`, `Description`, `Close`) for Four-Eyes approval modals with strict focus management and WAI-ARIA compliance.

---

## 2. Architectural Decisions

### D1: Tripartite Layout Architecture & Workstation Session State

- **Decision**: Mount the institutional cockpit at route `/cockpit` inside `FEIOS/web-prototype/src/app/cockpit/page.tsx` backed by a unified tripartite shell component (`src/components/cockpit/shell/tripartite-shell.tsx`). The layout enforces a 3-column + 1-bottom-shelf desktop structure:
  - **Left Triage Rail** ($300\text{px}$ fixed width, scrollable inbox): Persona-specific queues (alerts, partners, briefs, ledger events).
  - **Center Copilot Dossier** ($560\text{px}$ flexible width, high readability): Synthesized narratives, evidence tables, trade-off cards, and SAR draft composers.
  - **Right Kinetic Analytical Canvas** (flex-1 remainder, $\ge 580\text{px}$): Interactive SVG/Canvas visualizations (4-domain Causal DAG, topological property graphs, churn radar scatter, sub-affiliate tree).
  - **Bottom Governed Action Shelf** ($64\text{px}$ docked, expandable to $280\text{px}$): Two-phase commit Action Intent staging tray with Cloud KMS signature badges and Four-Eyes authorization controls.
- **Rationale**:
  - Palantir Foundry / Workshop and intelligence operational platforms rely on simultaneous situational context (triage list + entity dossier + relational/causal graph + governance shelf).
  - Keeps operator workflows in a single cohesive workspace without context-switching between fragmented tabs or pages.
  - Client state is managed via a focused React Context / reducer (`CockpitContext`), maintaining active persona, selected entity ID, staged actions, and simulation parameter sliders.
- **Alternatives Considered**:
  - *Full Multi-page routing (`/cockpit/executive`, `/cockpit/aml`, etc.)*: Rejected because role-switching within an operational crisis or triage flow causes disruptive page reloads and loses uncommitted draft action tokens.
  - *Tabbed Single Pane (switching full screen between inbox, dossier, and graph)*: Rejected because operators cannot cross-reference the graph nodes while reading the dossier evidence narrative.

---

### D2: QuantumBlack Design System & Institutional Light Mode Tokens

- **Decision**: Implement an uncompromising **Institutional Light Mode** inspired by the QuantumBlack Design System and Palantir Foundry, implemented via Tailwind CSS v4 `@theme` tokens in `FEIOS/web-prototype/src/app/globals.css`:
  - **Canvas Background**: `#f8fafc` (Slate 50) canvas ground providing crisp contrast against pure white cards.
  - **Card/Surface Background**: `#ffffff` (Pure White) with crisp `1px solid #e2e8f0` (Slate 200) borders and subtle `shadow-[0_1px_2px_rgba(15,23,42,0.04)]`.
  - **Primary Accents**: `#0f172a` (Slate 900) deep slate-navy for navigation rails, headers, active tabs, and primary actions; `#1e293b` (Slate 800) for secondary accents.
  - **Typography**: Inter / system monospace stack (`font-mono` for figures, timestamps, identifiers, and cryptographic hashes) with tabular numbers (`tabular-nums`) and strict letter-spacing scales.
  - **Status & Provenance Accents**:
    - Verified Causal Vector / Valid Integrity: `#059669` (Emerald 600) / `#ecfdf5` (Emerald 50)
    - Correlation Only / Unverified Causal Edge: `#d97706` (Amber 600) / `#fffbeb` (Amber 50)
    - Fallback Replay Badge: `#b45309` (Amber 700 text, `#fef3c7` ground, amber border)
    - High-Severity Violation / Risk Alert: `#dc2626` (Red 600) / `#fef2f2` (Red 50)
    - Governed Action Pending / Staged: `#2563eb` (Blue 600) / `#eff6ff` (Blue 50)
  - **Zero Dark-Mode Policy**: Strictly omit dark-mode toggles, CSS media dark queries, and invert classes to ensure 100% adherence to institutional light-mode design guidelines.
- **Rationale**:
  - High-density enterprise operators (analysts, compliance officers, executives) spend 8+ hours analyzing dense data tables, graphs, and audit trails. Institutional light mode ensures maximum legibility, eliminates eye strain caused by high-contrast dark-mode glowing lines, and mirrors regulatory paper audit trails.
- **Alternatives Considered**:
  - *Cyberpunk / High-contrast Dark Mode (glowing neon lines on black)*: Rejected. Violates user specification ("inspiration from palantir and using quantumblack design system (light mode)") and fails institutional compliance aesthetic standards.
  - *Tailwind v3 `tailwind.config.js` approach*: Rejected. The project already uses Tailwind v4 with `@theme` in `globals.css`.

---

### D3: Deterministic Metric Provenance Popovers (`@radix-ui/react-popover`)

- **Decision**: Encapsulate every displayed scalar metric in a `<MetricProvenanceBadge>` component powered by `@radix-ui/react-popover` (or accessible Radix primitive). On hover or click, the component renders a popover containing:
  - **Metric Identifier**: Canonical ID (e.g. `metric:fin:net_revenue`, `metric:aml:turnover_ratio`)
  - **Semantic Definition Version**: Semantic version and hash (e.g. `v2.4.1 [d8a9f2]`)
  - **As-Of Timestamp**: Exact ISO 8601 calculation timestamp (e.g. `2026-10-10T08:15:00Z`)
  - **Origin Engine**: Calculation engine (e.g. `duckdb:semantic_layer`, `bigquery:metrics_job`)
  - **Steward Role**: Responsible human steward (e.g. `VP Finance`, `Lead AML Risk Officer`)
  - **Citation Status**: Constitution Principle V label: `[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, or `[SPIKE]`.
- **Rationale**:
  - Directly enforces **Constitution Principle I** ("LLMs Never Compute Business Metrics") and **Principle V** ("Provenance and Labelling").
  - Operators and regulators must never encounter an unverified, unattributed figure.
  - Radix UI Popover ensures full keyboard navigation (Escape to dismiss, focus trap, arrow keys, screen reader WAI-ARIA compliance).
- **Alternatives Considered**:
  - *Browser standard `title` tooltips*: Rejected. `title` tooltips are inaccessible on touch/keyboard, do not support formatted typography, cannot be copied, and provide an inferior user experience.
  - *Global bottom drawer for provenance*: Rejected. Destroys spatial context; operators need to see the lineage immediately adjacent to the figure they are questioning.

---

### D4: Causal DAG, Topological Graph & Analytical Horizon Visualizations

- **Decision**: Implement interactive SVG/Canvas graph visualizers (`CausalDagCanvas`, `TopologicalGraphCanvas`, `WaterfallAttributionChart`, `ChurnRadarScatter`) using native React SVG rendering with optimized math:
  - **Causal DAG**: Hierarchical directed acyclic graph layout with distinct visual styling for verified causal edges (solid stroke `#059669`, marker arrow, refuter badge $p > 0.05$) vs correlation-only edges (dashed stroke `#d97706`, label "correlation detected; insufficient evidence for causation" pursuant to Principle III).
  - **What-If Parametric Propagation**: In-memory parametric DAG evaluator in TypeScript executing $< 5\text{ms}$ updates upon slider drag, recalculating forward 30/60/90-day EBITDA projections and rendering a waterfall attribution chart that strictly guarantees $\sum \Delta_{\text{components}} = 100\% \pm 0.01\%$.
  - **Topological Graph & Hub Suppression**: AML network canvas supporting node degree thresholding ($\text{degree} > K \implies \text{suppressed}$) to eliminate false-positive account merges from high-degree CGNAT proxies and public hosting IP addresses.
  - **Interactive Controls**: Zoom, pan, node selection linking directly to the Center Copilot Dossier, and edge inspection modals.
- **Rationale**:
  - Avoids heavyweight 3rd-party graph engine overhead while ensuring zero hydration mismatches in React 19.
  - Sub-200ms what-if interaction requirement (FR-008, SC-003) requires local parametric propagation without blocking network round-trips for slider dragging.
- **Alternatives Considered**:
  - *Full Cytoscape.js or WebGL Three.js bundle*: Rejected as over-engineered for 20–100 node operational subgraphs; introduces heavy bundle weight, hydration complexities with React 19, and canvas rendering artifacts.
  - *Server-rendered static PNG/SVG images*: Rejected. Disallows real-time slider manipulation, node clicking, and interactive CGNAT hub filtering.

---

### D5: Two-Phase Commit Governed Action Shelf & Four-Eyes Modal (`@radix-ui/react-dialog`)

- **Decision**: Implement the bottom docked `<GovernedActionShelf>` adhering to the two-phase commit protocol:
  1. **Phase 1: Stage Intent**: Operators stage proposals from dossiers or canvases (`HoldWithdrawal`, `LaunchRetentionPlaybook`, `FreezePartnerCommission`, `TuneMonitoringThreshold`). Each staged item generates an `ActionIntentToken` displaying intent ID, target entity, parameter diff, Cloud KMS signature placeholder (`ECDSA P-256`), and expiration timer ($15\text{min}$).
  2. **Phase 2: Authorize & Commit**:
     - *Low/Medium Severity*: Single authenticated operator sign-off commits to simulated write-back sink.
     - *High Severity* (`HoldWithdrawal`, `FreezePartnerCommission`): Requires **Four-Eyes Authorization**. Clicking Commit opens a `<FourEyesApprovalModal>` (built on Radix Dialog) requiring a second distinct officer identity credential (`officer_2_id` $\ne$ `initiator_id`), IdP claim validation, and dual digital sign-off.
- **Rationale**:
  - Strictly enforces **Constitution Principle II** ("No Autonomous Write-Back (NON-NEGOTIABLE)").
  - Under no circumstances can an agent or single click autonomously execute destructive real-world mutations.
  - Radix UI Dialog ensures accessible modal trapping, screen reader announcing, and keyboard dismissal.
- **Alternatives Considered**:
  - *Single-click direct execution*: Rejected. Explicitly forbidden by Constitution Principle II.
  - *External email/ticket workflow*: Rejected for simulated real-time cockpit demo; the two-phase commit shelf provides instant visual feedback while honoring compliance guarantees.

---

### D6: Deterministic Fallback & Replay Badging

- **Decision**: Implement `<FallbackReplayBanner>` and card-level `[REPLAY]` badges. When the live reasoning or synthesis engine encounters a simulated 503 outage or quota limit:
  - Dossier components degrade to cached domain snapshots generated by `FEIOS/src/eios/cockpit/fallback.py`.
  - Every cached card renders a prominent amber status badge: `[REPLAY] Cached as of YYYY-MM-DD HH:MM:SS UTC`.
  - Scalar metrics and causal DAG parameters continue to calculate deterministically.
- **Rationale**:
  - Directly enforces **Constitution Principle VIII** ("Deterministic Fallback and Operability").
  - Enterprise systems must never show blank pages, fatal unhandled exceptions, or unverified hallucinations when AI services degrade.
- **Alternatives Considered**:
  - *Blank loading spinner or generic error toast*: Rejected. Destroys operator productivity during operational crises.

---

### D7: Verification & Testing Strategy

- **Decision**: Multi-tier testing suite:
  1. **Unit & Component Testing**: Vitest / React Testing Library testing all 5 workstation views, tripartite layout rendering, metric provenance hover triggers, Four-Eyes modal gate enforcement, and what-if attribution sum invariance ($100\%$).
  2. **Contract Consistency Testing**: TypeScript schemas validating against JSON Schema contracts in `specs/012-cockpit/contracts/` and `specs/016-cockpit-frontend/contracts/`.
  3. **Accessibility (a11y) Audit**: Verify contrast ratios ($\ge 4.5:1$ on light ground), keyboard navigability, WAI-ARIA popover/dialog triggers.
  4. **Browser Verification**: Browser subagent verification loading `/cockpit`, switching roles, interacting with what-if sliders, clicking provenance popovers, and staging actions.
- **Rationale**:
  - Complies with Constitution Delivery Workflow and Quality Gates, guaranteeing zero regression across existing backend and frontend components.

---

### D8: Connected Backend-Frontend Bridge & Dual-Mode Execution

- **Decision**: Implement a production-grade API bridge architecture:
  1. **Python Cockpit API Gateway**: Expose a lightweight FastAPI server in `FEIOS/src/eios/cockpit/server.py` (and CLI `python -m eios.cockpit.server`) wrapping `CockpitShellPresenter`, `ExecutiveCockpitService`, `AMLWorkstationService`, `PartnerWorkstationService`, `ComplianceExplorerService`, `DataPlatformOperationsService`, `GovernedActionShelf`, `MetricAuditorGate`, and `DecisionOutcomesLedger`.
  2. **Next.js App Router API Route Handlers**: Mount route handlers in `FEIOS/web-prototype/src/app/api/cockpit/`:
     - `GET /api/cockpit/workstations/[role]` -> fetches complete tripartite workstation view.
     - `POST /api/cockpit/simulate` -> executes parametric what-if propagation.
     - `POST /api/cockpit/actions/stage` -> stages governed action token.
     - `POST /api/cockpit/actions/authorize` -> records Four-Eyes dual signature and commits to simulated sink.
     - `POST /api/cockpit/copilot/query` -> evaluates natural language query through the Metric Auditor Gate.
     - `POST /api/cockpit/flywheel/feedback` -> records human corrections into the Flywheel ledger.
     - `GET /api/cockpit/audit/verify` -> runs cryptographic SHA-256 chain verification.
  3. **Dual-Mode Execution (Principle VIII)**:
     - **Connected Live Mode**: When the Python backend is reachable (`http://127.0.0.1:8000`), the Next.js routes fetch live data.
     - **Deterministic Replay Mode**: When the Python backend is offline or during LLM outages, the API route seamlessly serves cached snapshot fixtures generated directly by `eios.cockpit.fallback`, stamping cards with amber `[REPLAY]` badges.
  4. **Zero Contract Drift**: Both Python (`schemas.py`) and TypeScript validate against the identical JSON Schemas in `specs/012-cockpit/contracts/` and `specs/016-cockpit-frontend/contracts/`.
- **Rationale**:
  - Guarantees that the frontend is a real production client for the EIOS operating system, completely eliminating disconnected toy mockups.
  - Honors Principle VIII (Deterministic Fallback) by providing continuous operation under backend downtime.
- **Alternatives Considered**:
  - *Hardcoded TypeScript mock data only*: Rejected as a disconnected toy product that ignores 15 features of real Python domain engineering.
  - *Raw WebSocket only without HTTP routes*: Rejected because operational queries and ledger audits require deterministic idempotent HTTP request/response semantics.

---

### D9: Full 15-Feature End-to-End Coherence

- **Decision**: Ensure that every single subsystem from Features 001–015 is explicitly surfaced and interactive in the Cockpit:
  - **F001**: Cloud KMS Keyring ID badges on staged action cards, IdP operator identity claims.
  - **F002**: Dataset seed/SHA citations in metric provenance badges.
  - **F003**: 6 Data Product SLA freshness monitors ($< 30$s) and DLQ quarantine counters on Operations Board.
  - **F004**: Governed Semantic Metric Layer with DuckDB/BigQuery provenance popovers and 0-hallucination Auditor Gate.
  - **F005**: RL-1..RL-7 Red-Line test gates and model benchmark margin cards on Quality tab.
  - **F006**: 4-domain Causal DAG, DoWhy refuters ($p > 0.05$), sub-200ms What-If shock propagation, 100% additive attribution waterfall.
  - **F007**: Omnipresent Conversational Copilot Command Bar with Auditor Gate.
  - **F008**: Churn Hazard Radar ($P(\text{churn}) \times \text{VaR}$), change-point decay indicators, VIP retention playbooks.
  - **F009**: Mirror trading pairs ($\ge 85\%$ co-occurrence), 3-tier referral tree, commission clawback intents.
  - **F010**: AML alert clustering (2,000 to $\le 50$), one-screen evidence dossier, kinetic graph with CGNAT hub suppression ($k > 100$), SAR draft composer.
  - **F011**: Two-phase commit Governed Action Shelf, Cloud KMS ECDSA P-256 signatures, Four-Eyes authorization dialog, monotonic `ledger_seq`, SHA-256 hash chaining verifier, WORM anchor proofs.
  - **F012**: 5 persona workstations, tripartite COP shell, QuantumBlack institutional light tokens.
  - **F013**: 10-SLO continuous evaluation, error budget burndowns, data drift alerts (KS test, PSI).
  - **F014**: Active Learning Flywheel feedback buttons ("Approve SAR", "Flag False Positive", "Adjust Risk Weight") writing to Decision Outcomes Ledger.
  - **F015**: Disaster Recovery Runbook execution proofs, automated KMS key rotation drills, chaos injection indicators, warm-start cache status.
- **Rationale**:
  - Ensures full institutional rigor: the frontend is the unified manifestation of the entire enterprise intelligence engagement.

---

## 3. Summary of Technical Choices & Resolutions

| Topic | Resolution | Context7 MCP Reference |
|---|---|---|
| **App Framework** | Next.js 16.3.6 App Router (`src/app/cockpit/page.tsx`) | `/vercel/next.js` |
| **Backend Integration** | Next.js API Routes (`src/app/api/cockpit/`) + FastAPI Server (`eios.cockpit.server`) | `/vercel/next.js` |
| **UI Library** | React 19.2.8 (Client Components with `'use client'`) | `/vercel/next.js` |
| **CSS System** | Tailwind CSS v4.0.0 (`@theme` in `globals.css`, Institutional Light Tokens) | `/tailwindlabs/tailwindcss.com` |
| **Accessible Primitives** | Radix UI Popover & Dialog Primitives | `/websites/radix-ui_primitives` |
| **Iconography** | `lucide-react` v0.475.0 (Clean institutional stroke icons) | Project `package.json` |
| **State Management** | React Context + useReducer (`CockpitState`, `CockpitAction`) | Native React 19 |
| **Graph Rendering** | Native SVG components (`CausalDagCanvas`, `TopologicalGraphCanvas`) | Native React SVG |
| **Verification** | Vitest + Testing Library + Python Pytest Contract Suite + Browser Subagent | Workspace standard |
