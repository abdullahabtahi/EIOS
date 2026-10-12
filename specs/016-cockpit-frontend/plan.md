# Implementation Plan: Institutional Operator Cockpit & QuantumBlack Design System Frontend (016-cockpit-frontend)

**Branch**: `016-cockpit-frontend` | **Date**: 2026-10-10 | **Spec**: [spec.md](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/specs/016-cockpit-frontend/spec.md)

**Input**: Feature specification from `specs/016-cockpit-frontend/spec.md`  
**Research & Decisions**: [research.md](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/specs/016-cockpit-frontend/research.md)  
**Data Model**: [data-model.md](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/specs/016-cockpit-frontend/data-model.md)  
**Contracts**: [contracts/](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/specs/016-cockpit-frontend/contracts/)  
**Quickstart**: [quickstart.md](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/specs/016-cockpit-frontend/quickstart.md)

---

## Summary

Deliver a production-grade, high-density Common Operational Picture (COP) frontend inspired by Palantir Foundry and the QuantumBlack Design System. The implementation mounts a tripartite operational workspace at `/cockpit` inside `FEIOS/web-prototype`, backed by a connected Python FastAPI API bridge (`FEIOS/src/eios/cockpit/server.py`) and Next.js App Router API Route Handlers (`src/app/api/cockpit/`). It enforces institutional light mode (`#ffffff` panel cards, `#f8fafc` canvas ground, `#0f172a` slate-navy accents, crisp 1px `#e2e8f0` borders, zero dark mode). It unifies all 15 backend subsystems (Features 001–015) into 5 specialized operator workstations (`Executive Decision Cockpit`, `AML Investigator Workstation`, `Partner Manager Workstation`, `Compliance Ledger Explorer`, and `Data Platform Operations Board`), deterministic metric provenance popovers (`@radix-ui/react-popover`), an omnipresent Copilot Command Bar with Metric Auditor Gate (F007), an interactive 4-domain causal DAG with sub-200ms parametric what-if simulation (F006), topological graph exploration with CGNAT proxy hub suppression (F010), Active Learning Flywheel feedback controls (F014), Disaster Recovery Runbook proofs (F015), a two-phase commit Governed Action Shelf with Four-Eyes authorization dialogs (`@radix-ui/react-dialog`) (F011), and deterministic fallback with amber `[REPLAY]` badges (Principle VIII).

---

## Technical Context

**Language/Version**: TypeScript 5.0+, React 19.2.8, Next.js 16.3.6 (App Router), Python 3.11+ (Backend EIOS Cockpit Services)  
**Primary Dependencies**:
- `@radix-ui/react-popover` (Accessible metric provenance triggers)
- `@radix-ui/react-dialog` (Four-Eyes approval authorization modal)
- `@radix-ui/react-slot` (Composition primitive)
- `tailwindcss` v4.0.0 with `@tailwindcss/postcss` (`@theme` institutional design system tokens)
- `lucide-react` v0.475.0 (Precision iconography)
- `clsx` & `tailwind-merge` (Dynamic utility class composition)
- `fastapi` & `uvicorn` (Python EIOS Cockpit API Gateway)

**Storage & Communication**:
- Client-side: In-memory React Context/Reducer (`CockpitSession`, staged action tokens, simulation state)
- Backend Bridge: Next.js API Routes (`src/app/api/cockpit/...`) communicating with live Python FastAPI Cockpit Server (`http://127.0.0.1:8000`), with zero-drift fallback to pre-compiled contract fixtures from `FEIOS/src/eios/cockpit/fallback.py` and `specs/012-cockpit/contracts/`
- Audit Storage: Monotonic WORM-anchored Decision Ledger with SHA-256 hash chaining

**Testing**:
- Vitest + `@testing-library/react` + `@testing-library/user-event` (Frontend UI suites)
- Pytest (48/48 passing backend cockpit contract and service tests)
- TypeScript strict compiler check (`tsc --noEmit`)
- ESLint (`next lint`)
- Browser Subagent E2E demonstration and visual inspection

**Target Platform**: Modern Desktop Web Browsers (Chrome, Edge, Safari, Firefox), targeted at $1440 \times 900$ desktop workstation viewports and scalable from $1280 \times 800$ to $3840 \times 2160$

**Project Type**: Full-Stack Connected Web Application (Next.js App Router Client + Python EIOS Backend Gateway)

**Performance Goals**:
- Initial page load & hydration: $< 800\text{ms}$
- Persona workstation tab switch: $< 50\text{ms}$ (instant client state switch)
- What-if shock slider parametric propagation: $< 200\text{ms}$ (in-memory DAG recalculation)
- Metric provenance popover open latency: $< 50\text{ms}$
- Action Intent staging & token card rendering: $< 50\text{ms}$
- Conversational Copilot Auditor Gate evaluation: $< 150\text{ms}$

**Constraints**:
- Strict Institutional Light Mode only: zero dark mode toggles or inverted styles.
- Constitution Invariant: LLMs Never Compute Business Metrics (Principle I) — 100% of figures must display deterministic provenance tool metadata.
- Constitution Invariant: No Autonomous Write-Back (Principle II) — High-severity mutations require explicit Four-Eyes human authorization.
- Constitution Invariant: Honest Uncertainty (Principle III) — Causal DAG edges that fail refuter checks must render dashed and labeled as correlation only.
- Constitution Invariant: Deterministic Fallback (Principle VIII) — Cached snapshots must display amber `[REPLAY]` badges with timestamp.
- No Disconnected Products: The frontend must talk directly to the Python EIOS presentation engine, sharing 100% contract schema parity.

**Scale/Scope**:
- 5 Operator Workstations covering all 15 platform subsystems (F001–F015)
- 1 Tripartite Shell (Left Rail, Center Dossier, Right Kinetic Canvas, Bottom Governed Action Shelf, Top Copilot Command Bar)
- 24 Functional Requirements (`FR-001` through `FR-024`)
- 8 Measurable Success Criteria (`SC-001` through `SC-008`)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Constitution Mandate | Feature 016 Architectural Compliance | Status |
|---|---|---|---|
| **I. LLMs Never Compute Business Metrics** | Quantitative values MUST come from deterministic tools, not LLM generations. | Every scalar metric in cards, tables, and charts is rendered via `<MetricProvenanceBadge>` showing Metric ID, semantic definition version, calculation engine, and as-of timestamp. Free-text figures are disallowed. | **PASS** |
| **II. No Autonomous Write-Back (NON-NEGOTIABLE)** | Zero agent-callable execute tools. Mutations require signed Action Intents, single-use nonces, and human approval (Four-Eyes for high severity). | Staged mutations appear in the docked `<GovernedActionShelf>` as pending Action Intent Tokens. High-severity actions require dual officer sign-off via `<FourEyesApprovalModal>`. No automated write-back exists. | **PASS** |
| **III. Honest Uncertainty & Causal Gate** | Causal assertions must pass refuter checks ($p > 0.05$, placebo $\approx 0$, confidence $\ge 0.80$). Otherwise state "correlation detected". | `<CausalDagCanvas>` evaluates edge refutation status: validated edges render solid green vectors with refuter statistics; unverified edges render dashed amber vectors explicitly labeled "correlation detected; insufficient evidence for causation". | **PASS** |
| **IV. Data as a Product, Ontology-Only Access** | Cockpit consumes data products only through Ontology contracts, never raw tables. | The frontend binds exclusively to structured view contracts validated against JSON Schemas (`specs/012-cockpit/contracts/` & `specs/016-cockpit-frontend/contracts/`). | **PASS** |
| **V. Provenance & Labelling** | Every figure or claim MUST carry one of `[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]`. | Metric badges display provenance classification and metadata popovers pursuant to Constitution Principle V. | **PASS** |
| **VI. Eval-First, Baselines & Anti-Circularity** | Tests written before implementation with $\ge 80\%$ test coverage. | Frontend components, reducers, and validators are backed by Vitest / Testing Library suites verifying all user stories, edge cases, and invariants. Backend backed by 48 passing pytest contract tests. | **PASS** |
| **VII. Specialised Agents & Decoupled Pipelines** | Bounded presentation surfaces for decoupled sub-agents; SCM refutation calculated offline; only parametric propagation interactive. | Interactive What-If slider performs parametric propagation over pre-computed DAG equations locally in $< 5\text{ms}$; heavy structural causal refutation is kept offline. | **PASS** |
| **VIII. Deterministic Fallback & Operability** | Outages must degrade to cached output labeled with `[REPLAY]` badges, never invented output. | Outages trigger `<FallbackReplayBanner>` and card-level amber `[REPLAY]` badges with exact generation timestamp. Interactive calculations continue offline. | **PASS** |

**Constitution Gate Outcome**: **PASS**. Zero unmitigated violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/016-cockpit-frontend/
├── spec.md                  # Feature Specification (ratified, 24 FRs, 15 features)
├── plan.md                  # This implementation plan
├── research.md              # Phase 0 Context7 research & architectural decisions (D1-D9)
├── data-model.md            # Phase 1 Domain entities and TypeScript types
├── quickstart.md            # Phase 1 Runnable validation guide & full-stack scenarios
├── contracts/               # Phase 1 UI contract schemas
│   └── cockpit-ui-contract.schema.json
├── checklists/
│   └── requirements.md      # Spec quality checklist (16/16 verified)
└── tasks.md                 # Phase 2 Implementation task breakdown (generated via /speckit-tasks)
```

### Source Code Architecture

```text
# Python Backend Gateway (FEIOS/src/eios/cockpit/)
FEIOS/src/eios/cockpit/
├── server.py                         # FastAPI Cockpit API Gateway & CLI runner
├── executive.py                      # Executive Morning Briefing & What-If SCM simulation
├── aml.py                            # AML alert triage, entity dossier & network graph
├── partner.py                        # Partner churn radar & mirror trading detection
├── compliance.py                     # Decision Ledger explorer & WORM proof verifier
├── operations.py                     # Data product SLA monitors & 10-SLO monitor
├── governance_shelf.py               # 2PC Action Intent state machine & Four-Eyes gate
├── session.py                        # RBAC session manager & tab permissions
├── provenance.py                     # Metric provenance resolver & latency SLA tracker
├── fallback.py                       # Cached snapshot generator for [REPLAY] mode
├── tokens.py                         # Canonical institutional design tokens & contrast validator
└── schemas.py                        # Draft 2020-12 contract validator

# Next.js Full-Stack Frontend (FEIOS/web-prototype/src/)
FEIOS/web-prototype/src/
├── app/
│   ├── globals.css                   # QuantumBlack design system @theme tokens (light mode)
│   ├── layout.tsx                    # Root layout
│   ├── page.tsx                      # Landing page with Launch Cockpit CTA
│   ├── cockpit/
│   │   └── page.tsx                  # Cockpit entry route mounting CockpitShell
│   └── api/
│       └── cockpit/
│           ├── workstations/
│           │   └── [role]/route.ts   # Workstation state fetcher (Live or Fallback)
│           ├── simulate/route.ts     # What-If parametric shock propagation endpoint
│           ├── actions/
│           │   ├── stage/route.ts    # Stage Action Intent token
│           │   └── authorize/route.ts# Four-Eyes dual approval commit endpoint
│           ├── copilot/
│           │   └── query/route.ts    # Natural language query via Auditor Gate
│           ├── flywheel/
│           │   └── feedback/route.ts # Human feedback submission to Flywheel ledger
│           └── audit/
│               └── verify/route.ts   # SHA-256 hash chain verification endpoint
├── components/
│   ├── cockpit/
│   │   ├── shell/
│   │   │   ├── tripartite-shell.tsx  # Tripartite grid container (Left, Center, Right, Bottom)
│   │   │   ├── header-nav.tsx        # Header with persona selector & system health
│   │   │   ├── copilot-command-bar.tsx# Omnipresent NL copilot query bar + Auditor Gate (F007)
│   │   │   ├── triage-rail.tsx       # Left triage rail inbox & filter controls
│   │   │   ├── copilot-dossier.tsx   # Center dossier view container
│   │   │   ├── kinetic-canvas.tsx    # Right kinetic visualizer container
│   │   │   └── governed-action-shelf.tsx# Bottom two-phase commit action tray
│   │   ├── workstations/
│   │   │   ├── executive-cockpit.tsx # Executive morning briefing & what-if scenario view
│   │   │   ├── aml-workstation.tsx   # AML alert triage, evidence dossier & SAR composer
│   │   │   ├── partner-workstation.tsx# Partner churn radar, 3-tier tree & mirror trading view
│   │   │   ├── compliance-explorer.tsx# Decision ledger SHA-256 timeline & WORM verification
│   │   │   └── operations-board.tsx  # Data product SLAs, 10-SLOs, DR proofs & Flywheel tab
│   │   ├── common/
│   │   │   ├── metric-provenance.tsx # Deterministic popover badge (@radix-ui/react-popover)
│   │   │   ├── four-eyes-modal.tsx   # Dual-officer approval dialog (@radix-ui/react-dialog)
│   │   │   ├── fallback-replay-badge.tsx# Amber [REPLAY] fallback indicator
│   │   │   ├── flywheel-feedback.tsx # Human feedback capture component (F014)
│   │   │   ├── causal-dag-canvas.tsx # Interactive 4-domain causal DAG with refuter vectors
│   │   │   ├── what-if-slider.tsx    # Sub-200ms parametric shock slider & waterfall
│   │   │   ├── topological-graph.tsx # AML network sub-graph with CGNAT hub suppression
│   │   │   └── churn-radar-scatter.tsx# Partner churn scatter plot (VaR x P(churn))
│   │   └── state/
│   │       ├── cockpit-context.tsx   # React Context provider & reducer
│   │       ├── cockpit-types.ts      # Core TypeScript type definitions
│   │       └── fixtures.ts           # Pre-compiled verified contract fixtures
│   └── ui/
│       ├── popover.tsx               # Accessible Popover wrapper
│       └── dialog.tsx                # Accessible Dialog wrapper
└── tests/
    └── cockpit/
        ├── tripartite-shell.test.tsx # Shell layout & role switching test
        ├── copilot-command-bar.test.tsx# NL Copilot & Auditor Gate test
        ├── executive-cockpit.test.tsx# Briefing & what-if waterfall 100% sum test
        ├── aml-workstation.test.tsx  # AML dossier, hub suppression & SAR editor test
        ├── partner-workstation.test.tsx# Churn radar & mirror trading test
        ├── compliance-ops.test.tsx   # Ledger chain, SLOs & DR proofs test
        ├── metric-provenance.test.tsx# Popover trigger & metadata verification test
        └── governance-shelf.test.tsx # Two-phase commit & Four-Eyes gate test
```

**Structure Decision**: A connected full-stack design where Next.js App Router API route handlers communicate directly with the Python EIOS presentation engine (`eios.cockpit`), ensuring zero contract drift, dual-mode execution (connected live or offline deterministic replay), and complete coverage of all 15 features.

---

## Complexity Tracking

> **Constitution Check Violations**: NONE. Full compliance across Principles I–VIII.

| Potential Concern | Decision | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|---|
| Connected API vs Client-Only Mocks | Next.js API Routes + Python FastAPI Gateway | Eliminates disconnected toy mockups; unites 15 features of real Python domain engineering | Client-only mocks drift from backend schemas and fail production rigor |
| Native SVG vs 3rd-party graph engine | Custom React SVG graph components | Sub-200ms what-if slider updates, deterministic styling, zero React 19 hydration issues | Cytoscape / Three.js bundle is $> 500\text{KB}$, causes hydration mismatches, and over-complicates 20–100 node graphs |
| Strict Light Mode only | Single institutional light theme | Fulfills explicit user requirement, QuantumBlack design guidelines, and audit readability | Dark-mode toggles double CSS footprint and violate the ratified user specification |
| Four-Eyes Modal within Action Shelf | Radix Dialog modal gated commit | Enforces Constitution Principle II invariant | Single-click execution would fail safety and compliance mandates |
