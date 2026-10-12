# Phase 0 Research & Architectural Decisions: Executive Cockpit & Operator Workstations (012-cockpit)

**Feature**: Executive Cockpit & Operator Workstations (F11 / Slice S6)  
**Spec**: [`specs/012-cockpit/spec.md`](spec.md)  
**Authoritative References**: `initial_plan.md` §7, §6.1–6.3, `docs/archive/initial_plan_v2.md` §6, `docs/brief/monitoring.md`, `docs/brief/fraud.md`, `.specify/memory/constitution.md` (Principles I, II, III, IV, V, VI, VII, VIII)  
**Status**: Completed  

---

## 1. Architectural Decisions & Trade-Offs

### Decision 1: Institutional Light-Mode Token Architecture (Palantir Solution Designer × QuantumBlack Design System)

- **Context**: The user and engagement guidelines strictly prohibit dark mode. The user mandated high-contrast, institutional light mode matching Palantir Foundry Solution Designer (`#ffffff` panels, `#f4f6f8` canvas ground, slate-navy left rail `#1c2530`, text `#0f172a`, borders `#e2e8f0`) and QuantumBlack Design System (`QBDS` Base UI design tokens, 0px border radius).
- **Decision**: Define a formal institutional design token system:
  - Surface Background Ground: `--surface-ground: #f4f6f8` (subtle institutional cool grey)
  - Surface Primary (Cards/Panels): `--surface-card: #ffffff` (pure white, sharp contrast)
  - Surface Navigation Left Rail: `--surface-rail: #1c2530` (authoritative slate-navy)
  - Text Primary: `--text-primary: #0f172a` (high-contrast slate-900, contrast ratio $\ge 12.5:1$ against white)
  - Text Secondary: `--text-muted: #475569` (slate-600, contrast ratio $\ge 5.2:1$, WCAG 2.2 AA compliant)
  - Borders & Dividers: `--border-divider: #e2e8f0` (slate-200 crisp lines)
  - Geometry: `--radius-base: 0px` (sharp, zero border-radius throughout all cards, buttons, badges, and modals)
  - Status Accents: Verified Causal/Success `--accent-verified: #047857` (emerald-700), Caution/Replay `--accent-replay: #b45309` (amber-700), Severe/Breach `--accent-critical: #b91c1c` (rose-700), Information/Link `--accent-link: #0284c7` (sky-600).
- **Rationale**: Palantir and McKinsey/QuantumBlack design doctrines reject consumer dark modes in mission-critical analytical workstations because dark mode reduces legibility for dense tables, complex multi-hop graph edges, and typographic scan-lines over extended 8-hour operational shifts. Sharp 0px corners maximize data density and information-to-ink ratio.
- **Alternatives Considered**:
  - *Dark Mode Palette*: Rejected due to explicit user prohibition and reduced daylight readability for institutional operators.
  - *Generic Neutral Palette (Gray-50/Gray-100)*: Rejected because standard consumer web shades lack the authoritative, cool-cast slate undertone characteristic of Foundry and QBDS.

---

### Decision 2: Tripartite Common Operational Picture (COP) Layout & Window Management

- **Context**: Enterprise operators across all 5 personas need to review alert queues, drill down into evidence narratives, explore relational structures or causal models, and stage human approvals without modal lockup or losing context.
- **Decision**: Implement a deterministic 3-column fixed-fluid layout flanked by an anchored action shelf:
  1. *Column 1 (Left Rail / Triage Inbox)*: Fixed width ($320$px), non-scrolling header with facet filters (severity, age, discrepancy ratio), vertically scrolling triage items with real-time status pills.
  2. *Column 2 (Center / AI Copilot Dossier)*: Flexible width ($480$px min, $560$px default), structured narrative synthesizer displaying KYC/KYB discrepancies, DoWhy refuter test summaries, and automated SAR drafts.
  3. *Column 3 (Right / Kinetic Canvas & Explorer)*: Expansive canvas ($640$px min, flex-grow), hosting the 4-domain causal DAG, What-If shock simulation slider, interactive mule ring network graph, churn radar scatter, or cryptographic hash chain verification bar.
  4. *Bottom Docked Shelf (Governed Action Shelf)*: Fixed footer ($72$px collapsed, expandable to $360$px review drawer) hosting in-flight `ActionIntentToken` cards with Two-Phase Commit state progression.
- **Rationale**: Follows the military and intelligence Common Operational Picture (COP) paradigm where situational awareness (left), synthesis/intelligence (center), and spatial/relational evidence (right) are always concurrently visible, enabling immediate triage-to-action workflows without navigation context loss.
- **Alternatives Considered**:
  - *Tabbed Single-Pane Dashboard*: Rejected because forcing operators to click back and forth between alerts, dossiers, and network graphs destroys investigative momentum and increases mean time to resolve (MTTR).
  - *Floating Multi-Window Desktop Layout*: Rejected due to layout instability, window overlap, and poor responsiveness across varying desktop resolutions.

---

### Decision 3: Kinetic Network Graph & Dynamic High-Degree Hub Suppression

- **Context**: In AML mule rings and partner referral networks, centralized payment gateways, top affiliate hubs, or shared CGNAT IP addresses create high-degree nodes ($> 100$ to $> 500$ connections) that cause canvas freezes, layout explosions, and unreadable visual hairballs.
- **Decision**: Implement dynamic degree-based hub suppression and node clustering:
  - If a node degree $k > 100$, the layout engine activates Hub Suppression: leaf nodes sharing identical edge types are collapsed into a single meta-badge node (e.g. `[+46 Paired Accounts]`).
  - Expanding a collapsed cluster occurs only on explicit user click, loading sub-edges into a localized sub-canvas.
  - Layout computation is executed off the main thread (using web worker or precomputed server coordinates) with pinned positions for seed investigation entities.
  - Canvas target performance: $> 30$ FPS (targeting 60 FPS) for graphs up to 1,000 entities.
- **Rationale**: Adheres to `initial_plan.md` §3.3 & §5.4 (ADR-004), preventing shared hosting/CGNAT IPs from creating false syndicate merges and maintaining silky-smooth canvas interaction.
- **Alternatives Considered**:
  - *Unconstrained Force-Directed Graph*: Rejected because $> 200$ nodes cause continuous physics oscillation, high CPU utilization, and visual chaos.
  - *Static Paginated Tables*: Rejected because fraud rings and multi-hop mirror trading cannot be intuitively discovered without visual topological paths.

---

### Decision 4: Deterministic Metric Provenance & Instant Popover Protocol

- **Context**: Constitution Principle I and Invariant 1 mandate that LLMs never compute business metrics and that every quantitative scalar displayed across cards and dossiers must trace back to the Semantic Metric Registry.
- **Decision**: Implement a standardized `ProvenanceMetadata` contract and sub-50ms provenance cache:
  - Every scalar metric rendered in the UI is wrapped with an interactive badge binding `metric_id`, `definition_version`, `as_of_timestamp`, `computation_source`, and `owner_role`.
  - When the user hovers or clicks, a client-side popover renders instantly ($< 50$ ms) without triggering asynchronous backend round-trips.
  - If an agent narrative contains a numeric claim lacking registered provenance metadata, the Metric Auditor Gate masks the number, renders a warning pill, and logs a red-line violation.
- **Rationale**: Builds unwavering institutional trust. Executives and compliance officers can immediately verify the freshness, mathematical formula, and data steward for every number without opening documentation or data catalogs.
- **Alternatives Considered**:
  - *Footnotes / Bottom Citations*: Rejected because navigating to bottom footnotes disrupts narrative reading flow.
  - *Asynchronous Tooltip Lookups*: Rejected because network round-trips introduce a $200$–$500$ ms delay, making rapid hover inspection feel sluggish.

---

### Decision 5: Sub-200ms Parametric What-If Shock Propagation

- **Context**: C-level executives need an interactive slider to simulate shocks (e.g. competitor payout $+200$ bps, marketing budget shifts). However, full DoWhy causal DAG structure learning and refutation is computationally heavy (taking tens of seconds) and cannot run live.
- **Decision**: Enforce a strict offline/online architectural split:
  - Nightly batch pipelines fit the Structural Causal Model (SCM), run refuter tests, validate confidence gates ($\ge 0.80$), and cache parametric linear/non-linear structural equations.
  - The online cockpit What-If Shock Slider executes purely parametric propagation over the precomputed cached coefficients, updating downstream 30/60/90-day revenue deltas and attribution waterfalls within $< 200$ ms.
  - Attribution components are normalized to guarantee they mathematically sum to exactly $100\% \pm 0.01\%$.
- **Rationale**: Adheres to Constitution Principle VII (Decoupled Pipelines) and Invariant 4. Delivers instant interactive feedback to executives without compromising causal econometric rigor.
- **Alternatives Considered**:
  - *Live DoWhy Refutation on Every Slider Move*: Rejected because multi-second latency makes sliders unusable.
  - *Naive Linear Interpolation*: Rejected because it ignores conditional independence and structural mediator pathways.

---

### Decision 6: Deterministic Replay & Graceful Degradation Engine

- **Context**: In real enterprise environments, external LLM providers or network services occasionally suffer timeouts, latency spikes, or outages. Under no circumstances may the cockpit emit invented or ungrounded fallback text.
- **Decision**: Implement an automated Deterministic Fallback Engine:
  - If the live synthesis engine or LLM gateway returns a timeout ($> 3.5$s) or HTTP 5xx error, the cockpit service immediately serves the most recent verified cached snapshot.
  - The UI attaches a prominent amber `[REPLAY]` or `[CACHED]` status badge showing the exact as-of generation timestamp and a non-intrusive banner informing the operator that live streaming is temporarily degraded.
  - Rule-based diagnostic cards and pre-computed risk metrics continue to function without interruption.
- **Rationale**: Fulfills Constitution Principle VIII (Deterministic Fallback and Operability), demonstrating true enterprise production readiness under adversity.
- **Alternatives Considered**:
  - *Error Page / White Screen of Death*: Rejected because operators must maintain visibility into ongoing operations even during partial outages.
  - *Generic Fallback LLM Prompt*: Rejected because fallback LLMs without warm caches have high latency and could introduce hallucinated figures.

---

## 2. Research Summary & Technology Validation

| Research Item | Selected Approach | Key Benefit |
|---|---|---|
| **Design System Tokens** | High-contrast Light Mode (`#ffffff` panels, `#f4f6f8` ground, `#1c2530` rail, 0px radius) | Zero dark-mode eye strain; maximum data density; Palantir & QBDS rigor. |
| **Workspace Layout** | Tripartite Common Operational Picture (Left Triage, Center Dossier, Right Canvas, Bottom 2PC Shelf) | Zero context switching; streamlined triage-to-action workflow. |
| **Graph Interaction** | Dynamic Hub Suppression with cluster badges for nodes with degree $k > 100$ | Silky-smooth canvas interaction ($> 30$ FPS); eliminates hairballs. |
| **Provenance Protocol** | Sub-50ms client-side Provenance Popovers (`metric_id`, version, timestamp, steward) | 100% mathematical transparency; zero hallucination. |
| **Scenario Simulation** | Parametric shock propagation over precomputed cached SCM coefficients | $< 200$ ms interactive slider latency with 100% additive attribution. |
| **Fault Resilience** | Deterministic Replay Engine with prominent `[REPLAY]` badging | Robust operability during LLM outages without invented text. |
