@AGENTS.md


## 3. UI/UX Architecture & Institutional Ergonomics

The Web Cockpit implements the **Tripartite Common Operating Picture (COP)**:
- **Left Column (`<TriageRail />`)**: Priority triage queue, severity filters (Critical, High, Medium, Low), forensic search.
- **Center Column (`<CopilotDossier />`)**: Evidence dossier, Gemini 3.8 Flash causal synthesis, metric provenance tags.
- **Right Column (`<KineticCanvas />`)**: Role-specific interactive analytical surfaces.
- **Bottom Shelf (`<GovernedActionShelf />`)**: Two-phase commit action staging, Four-Eyes dual approval, KMS P-256 digital signing.
- **Global Modal (`<CopilotCommandBar />`)**: Cmd+K command bar with real-time Metric Auditor Gate verification.

### Strict Design Rules (Institutional Sovereign Light)
1. **Light Mode Only (analytical surfaces)**: 100% institutional light mode (`#fdfdfd` canvas, `#ffffff` elevated cards, `#e5e5e5` 1px borders, `#111111` headlines). No cyber-slop, no glowing dark themes, no decorative gradients.
   - **Scoped exception, dark global chrome**: exactly two elements are dark, the left navigation rail (`<AppNavRail />`, 48px icon strip that hover-expands to a 232px overlay) and the first row of the top header (`<HeaderNav />`: brand, telemetry, operator; the persona tab strip below it stays light). They use the `cockpit-rail` / `chrome-*` tokens in `globals.css` (`#1c2530` slate). Everything inside the three columns, the Kinetic Canvas studio bar and the action shelf stays light. No other dark surfaces.
2. **Strict 2-Header Maximum**:
   - **Header 1 (Global Shell)**: Top bar, dark first row + light persona strip (right of the nav rail) (`EIOS / OPERATOR COCKPIT v2.4` + 5 Global Workstation tabs: Executive, AML Investigator, Partner Manager, Compliance & Audit, Data Operations).
   - **Header 2 (Kinetic Canvas Studio Bar)**: Scoped exclusively to the right column (`KINETIC CANVAS: {ROLE} | Mode: {SECTION}` + segmented surface tabs + `Flywheel Feedback` trigger).
   - **Header 3 is STRICTLY BANNED**: Workstations must never render a redundant 3rd internal toolbar.
3. **Continuous Scrollable Workspaces**:
   - Workstations render all relevant analytical surfaces in a **continuous, vertically scrollable layout**.
   - Never isolate small 200px cards behind exclusive tab toggles that leave empty white space.
   - Implement **two-way scroll-spy synchronization**:
     - Clicking Header 2 tabs smoothly scrolls the container to that section anchor (`#panel-...`).
     - Scrolling updates the active tab and `Mode: <section>` text in Header 2 dynamically.

---

## 4. Workstations & Persona Role Matrix

The URL query parameter `?role=<role>` normalizes to one of 5 canonical `PersonaRole` values:

| `PersonaRole` | Workstation View | Anchor Surfaces |
|---|---|---|
| `executive` | `ExecutiveCockpitView` | `#panel-dag` (Causal DAG Canvas)<br>`#panel-whatif` (What-If Waterfall & Shock Slider)<br>`#panel-briefing` (4-Horizon Morning Briefing)<br>`#panel-tradeoffs` (Strategic Countermeasure Trade-offs) |
| `aml_investigator` | `AmlWorkstationView` | `#panel-graph` (Topological Relational Graph & CGNAT suppression)<br>`#panel-sar` (Near-Final SAR Draft Composer)<br>`#panel-dossier` (One-Screen Evidence Dossier) |
| `partner_manager` | `PartnerWorkstationView` | `#panel-radar` (2D Churn Hazard Radar $P(\text{churn}) \times \text{VaR}$)<br>`#panel-grid` (High-Density Portfolio Matrix - 20 cohorts)<br>`#panel-tree` (3-Tier Sub-Affiliate Tree & Collusion Detection)<br>`#panel-ontology` (Sovereign Kinetic Ontology 360 Inspector) |
| `compliance_auditor` | `ComplianceExplorerView` | `#panel-ledger` (Monotonic WORM Decision Ledger)<br>`#panel-verifier` (SHA-256 Hash Chain Verifier)<br>`#panel-dr` (Disaster Recovery Runbook Proofs) |
| `data_operations` | `OperationsBoardView` | `#panel-slos` (Streaming Ingestion & 10 SLO Burndowns)<br>`#panel-redlines` (Constitutional Red-Line Test Gates RL-1..7)<br>`#panel-dlq` (Dead Letter Queue Quarantine & Redrive)<br>`#panel-dr` (Platform Disaster Recovery Proofs) |

