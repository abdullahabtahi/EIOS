# Feature Specification: Executive Cockpit & Operator Workstations (F11 / Slice S6)

**Feature Branch**: `012-cockpit`  
**Created**: 2026-10-09  
**Status**: Draft  
**Authoritative References**: `initial_plan.md` §7, §6.1–6.3, `docs/archive/initial_plan_v2.md` §6, `docs/brief/monitoring.md`, `docs/brief/fraud.md`, `.specify/memory/constitution.md` (Principles I, II, III, IV, V, VI, VII, VIII)  
**Input**: User description: "Executive Cockpit & Operator Workstations (F11 / Slice S6): High-contrast institutional light mode Common Operational Picture (COP) with zero dark-mode, implementing 5 dedicated persona workstations (Executive Decision Cockpit, AML Investigator Workstation, Partner Manager Workstation, Compliance & Audit Explorer, Data Platform & Operations Board), tripartite layout (Triage Inbox, Copilot Dossier, Kinetic Graph / Horizon Canvas), two-phase commit governed action bar with Four-Eyes review, deterministic metric provenance popovers, honest uncertainty and refuter status indicators, and deterministic replay fallback under outages."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Universal Common Operational Picture (COP) Shell & Governance Invariants (Priority: P1) 🎯 MVP

As an **Enterprise Operator (any authenticated role)**,  
I want a unified, high-density, institutional light-mode tripartite operational interface featuring a left-rail triage inbox, center evidence copilot dossier, right kinetic analytical canvas, and bottom governed action shelf,  
So that I can monitor real-time enterprise risks, inspect causal narratives, explore relational structures, and stage human-in-the-loop decisions within a single coherent workspace without dark-mode visual fatigue or disjointed tooling.

**Why this priority**: The universal shell establishes the layout grid, institutional design system tokens, persona role-switching, streaming communication protocol, and non-negotiable cross-cutting invariants (deterministic metric provenance popovers, audit gates, and replay badging). Without this shell, no individual workstation can function safely.

**Independent Test**: Load the operator workstation across supported browser viewports (minimum $1440 \times 900$ desktop target); verify that the interface strictly enforces institutional light mode (`#ffffff` panel cards, `#f4f6f8` canvas ground, slate-navy left rail `#1c2530`, high-contrast text `#0f172a`, crisp `#e2e8f0` dividers, sharp 0px border radius, with zero dark-mode options); verify that hovering or clicking any scalar metric renders a deterministic Provenance Popover showing Metric ID, Definition Version, As-Of Timestamp, and Owner Role; verify that simulated service disruptions trigger immediate `[REPLAY]` or `[CACHED]` fallback badges pursuant to Constitution Principle VIII.

**Acceptance Scenarios**:

1. **Given** an authenticated operator loading the workspace,  
   **When** the interface initializes,  
   **Then** the shell renders the tripartite grid (Triage Inbox on the left, Dossier Synthesis in the center, Analytical Canvas on the right, and Governed Action Shelf anchored at the bottom) in pure institutional light mode with no dark-mode toggle or theme.
2. **Given** any quantitative figure displayed on any card, chart, or dossier narrative,  
   **When** the user clicks or hovers on the metric badge,  
   **Then** an inspector popover renders showing the deterministic metric identifier, ontology semantic definition version, calculation timestamp (`as-of`), calculation engine origin, and steward role, guaranteeing 100% provenance transparency pursuant to Constitution Principle V.
3. **Given** an underlying language model or synthesis engine outage,  
   **When** the operator accesses or refreshes any narrative view,  
   **Then** the interface displays the most recent cached snapshot stamped with an unambiguous amber `[REPLAY]` status badge and the exact generation timestamp, never emitting unverified or synthetic placeholder text.
4. **Given** an operator switching roles between Executive, AML Investigator, Partner Manager, Compliance Auditor, and Data Operations,  
   **When** the role selector is toggled,  
   **Then** the workspace dynamically updates permissions, filters triage queues, and restructures the center dossier and right canvas to the selected persona without losing uncommitted draft state.

---

### User Story 2 - Executive Decision Cockpit: Morning Briefing & Causal Simulation (Priority: P1)

As a **Chief Executive Officer & Chief Operating Officer**,  
I want an automated morning briefing feed covering 4 business horizons (Competitive, Partner, Client, Financial), an interactive 4-domain causal DAG with refuter validation gates, an interactive what-if shock slider, an additive attribution forecast summing to 100%, and strategic trade-off evaluation cards,  
So that I can immediately understand the macroeconomic and operational drivers of revenue and margin changes, test counterfactual strategic responses, and make governed executive decisions backed by causal evidence.

**Why this priority**: C-level executives require synthesized cross-domain explanations of business movements rather than siloed operational dashboards. Providing causal attribution with honest uncertainty guarantees that strategic capital decisions are grounded in mathematically refuted relationships.

**Independent Test**: Navigate to the Executive Decision Cockpit; verify the Morning Briefing feed loads the 4 horizons; verify the causal DAG highlights verified causal edges versus unverified correlations with explicit confidence badges; adjust the What-If Shock Slider (e.g. competitor commission hike $+15\%$, marketing budget shift $-\$50\text{k}$); verify that downstream financial impacts update within 200 ms via parametric propagation, and that attribution components sum to exactly $100\% \pm 0.01\%$.

**Acceptance Scenarios**:

1. **Given** the morning briefing is generated,  
   **When** the executive opens the cockpit,  
   **Then** the center pane renders a synthesized executive summary highlighting key insights, emerging operational risks, and market opportunities across Competitive, Partner, Client, and Financial horizons with citations to underlying data products.
2. **Given** the 4-domain causal DAG view,  
   **When** viewing relationships between competitive moves, partner activity, client churn, and financial net revenue,  
   **Then** edges passing refuter checks (placebo refuter $\approx 0$, confidence $\ge 0.80$) render as solid causal vectors, whereas edges failing refutation render as dashed lines labelled "correlation detected; insufficient evidence for causation" pursuant to Constitution Principle III.
3. **Given** the What-If Shock Slider on the scenario simulation card,  
   **When** the executive drags the shock parameter (e.g. "Competitor Payout $+200$ bps"),  
   **Then** the cockpit executes parametric propagation across the cached structural causal model within 200 ms, updating forward 30/60/90-day revenue projections and displaying a waterfall attribution chart whose components sum to exactly 100%.
4. **Given** alternative strategic options (e.g. "Match Competitor Spread" vs. "Deploy Retention VIP Packages" vs. "Hold Line"),  
   **When** reviewing the Trade-Off Evaluation Cards,  
   **Then** the cockpit displays side-by-side projected EBITDA impact, client churn probability delta, capital cost, and regulatory risk scores with deterministic confidence intervals.

---

### User Story 3 - AML Investigator Workstation: Entity Dossier, Kinetic Graph & SAR Composer (Priority: P1)

As a **Lead AML Compliance Investigator**,  
I want a prioritized alert triage queue, a one-screen unified entity dossier linking fiat and crypto transactions with declared KYC/KYB records, an interactive kinetic network graph revealing syndicate mule rings, an automated regulator-ready Suspicious Activity Report (SAR) draft composer, and governed two-phase commit account freeze controls,  
So that I can investigate complex cross-border financial crime syndicates in minutes and execute defensible, auditable regulatory actions.

**Why this priority**: Financial crime investigation is Deriv's highest legal risk surface. Investigators currently lose hours stitching together disparate logs; an integrated kinetic graph and dossier reduces investigation time by over 60% while eliminating human copying errors in regulatory filings.

**Independent Test**: Select a high-risk AML triage alert (e.g. Account #CR84920 flagged for deposit volume $1,600\%$ above declared monthly income); verify that the center panel populates the one-screen dossier with KYC/KYB discrepancy metrics; verify that the right panel renders the kinetic network graph displaying linked accounts, crypto payment agent clusters, and matched transaction timing; trigger SAR draft generation and verify that all narrative figures carry brief citations; stage a `HoldWithdrawal` action intent and verify that it requires Four-Eyes authorization.

**Acceptance Scenarios**:

1. **Given** an investigator reviewing the triage inbox,  
   **When** filtering alerts by severity,  
   **Then** items display composite AML risk scores, detected discrepancy ratios (e.g. "Declared $\$500$/mo; deposited $\$8,000$ USDT"), syndicate ring size, and age in queue.
2. **Given** an active investigation on an entity,  
   **When** inspecting the one-screen unified dossier,  
   **Then** the panel aggregates declared source-of-wealth records, fiat/crypto transaction velocity, pseudonymized identity cluster keys (`tok_id_cluster_<hex16>`), connected hardware fingerprints, and DoWhy refuter test results in a single non-scrolling tabbed view.
3. **Given** the kinetic network graph,  
   **When** an entity belongs to a mule syndicate ring,  
   **Then** the graph renders nodes (accounts, payment agents, IP/device clusters) and edges (transaction volume, matched timing links) with dynamic hub suppression for high-degree nodes ($> 100$ connections) to prevent canvas lockup.
4. **Given** a confirmed suspicion of money laundering,  
   **When** the investigator clicks "Draft SAR",  
   **Then** the SAR Composer generates a structured regulatory narrative following regulatory typologies, auto-populating transaction dates, amounts, and syndicate identities with clickable evidence links.
5. **Given** an urgent need to mitigate ongoing capital flight,  
   **When** the investigator selects "Hold Withdrawal" or "Freeze Account" from the governed action shelf,  
   **Then** the system opens a Two-Phase Commit modal, validates the KMS-signed `ActionIntentToken`, locks the action in `PENDING` status, and routes the token to the dual-approval queue pursuant to Constitution Principle II.

---

### User Story 4 - Partner Manager Workstation: Churn Radar, Hierarchy & Playbooks (Priority: P2)

As a **Senior Partner Account Manager & Business Development Director**,  
I want an interactive Churn Radar scatter plot (Lifetime Value $\times$ Churn Hazard), a geographic cohort anomaly map, a partner referral hierarchy with opposite-trading ring detection, and a governed retention playbook recommender,  
So that I can proactively retain top-tier introducing brokers (IBs) before they defect to competitors while identifying toxic partner networks that exploit commission structures.

**Why this priority**: Partner affiliates generate the majority of retail trading volume, but poaching by rival brokers causes severe revenue volatility. Timely detection of partner dissatisfaction combined with fraud ring isolation protects net revenue and brand integrity.

**Independent Test**: Load the Partner Manager Workstation; verify the Churn Radar scatter displays partners positioned by 30-day realized volume (Y-axis) versus churn probability (X-axis) with optimal intervention windows; click on a high-value at-risk partner (e.g. Partner #AP-1029); inspect the root-cause diagnosis (payout ticket delay, competitor spread comparison); view recommended retention deals; select a playbook within budget ($\le \$2,500$) and verify fast-path approval, or select a high-impact deal and verify approval routing.

**Acceptance Scenarios**:

1. **Given** the Churn Radar view,  
   **When** examining the partner distribution,  
   **Then** partners are categorized into quadrants (High Value / High Risk, High Value / Stable, Low Value / High Risk, Low Value / Stable) with visual callouts for partners entering the critical 14-day intervention window.
2. **Given** an at-risk partner selected on the radar,  
   **When** the partner dossier opens,  
   **Then** the dossier displays decay metrics (e.g. login frequency decay $-68\%$, first-time depositor count $-45\%$), support ticket sentiment, and competitor poaching intelligence with explicit source attribution.
3. **Given** a partner suspected of commission abuse,  
   **When** opening the Partner Hierarchy view,  
   **Then** the canvas visualizes the master affiliate, sub-affiliates, client nodes, and highlights opposite-trading ring pairs (e.g. paired BUY and SELL positions on synthetic indices executed within sub-second windows).
4. **Given** an unearned commission liability identified on an abusive partner,  
   **When** the manager stages a "Halt Partner Payouts & Clawback" action,  
   **Then** the governed action shelf generates an `ActionIntentToken` carrying the liability calculation and routes it for High-severity Four-Eyes sign-off.
5. **Given** a legitimate at-risk partner recommended for retention,  
   **When** the manager selects "Deploy VIP Spread Deal" with estimated cost $\le \$2,500$,  
   **Then** the action utilizes the single-approver fast-path, executing immediately upon the manager's authenticated sign-off.

---

### User Story 5 - Compliance & Audit Explorer: Cryptographic Ledger & WORM Proofs (Priority: P2)

As an **External Regulatory Auditor & Internal Compliance Inspector**,  
I want a timeline explorer of the monotonic decision ledger (`ledger_seq = 1, 2, 3...`), a real-time cryptographic hash chain verification bar, immutable WORM checkpoint inspection, and a complete Four-Eyes dual-approval audit trail,  
So that I can verify the mathematical integrity and legal defensibility of every agent recommendation and human sign-off with zero possibility of historical record manipulation.

**Why this priority**: Enterprise trust and regulatory licensing require unassailable evidence that decisions have not been retroactively altered. A visual audit explorer enables auditors to independently verify cryptographic hash continuity and WORM retention compliance without writing manual SQL queries.

**Independent Test**: Open the Compliance & Audit Explorer; verify the continuous timeline of ledger events sorted by atomic sequence number; trigger the visual hash chain verifier across the active block of transactions; confirm 100% unbroken cryptographic links ($H_i = \text{SHA-256}(H_{i-1} \parallel \text{seq}_i \parallel \text{payload}_i)$); inspect a periodic WORM checkpoint record with its Cloud Storage Object Retention lock proof; review high-severity decision records to verify distinct dual approver identities and timestamps.

**Acceptance Scenarios**:

1. **Given** the decision ledger explorer,  
   **When** inspecting recorded events,  
   **Then** every entry displays its atomic strictly monotonic sequence number (`ledger_seq`), event timestamp, event type, actor ID, and cryptographic payload digest.
2. **Given** the hash chain verification tool,  
   **When** the auditor clicks "Verify Cryptographic Continuity",  
   **Then** the system sequentially validates every hash link from genesis anchor to chain-head, rendering an unbroken green verification bar with total verified records and current root hash.
3. **Given** a periodic WORM anchor checkpoint,  
   **When** the auditor inspects the checkpoint card,  
   **Then** the card displays the anchored chain-head sequence, root hash digest, immutable retention policy expiration date, and verified compliance lock status.
4. **Given** a High-severity action (e.g. `HoldWithdrawal` or `ClawbackCommission`),  
   **When** viewing the execution audit trail,  
   **Then** the explorer displays the original agent proposal token, KMS asymmetric signature, the first approver's identity and timestamp, the second approver's identity and timestamp, and the write-back execution receipt.

---

### User Story 6 - Data Platform & Operations Board: Contracts, Freshness & Lineage (Priority: P3)

As a **Lead Data Engineer & Forward-Deployed Platform Engineer**,  
I want a real-time Data Quality (DQ) board displaying data contract breaches, ingestion freshness SLA monitors, identity cluster conflict resolution queues, and semantic metric catalog lineage topologies,  
So that I can ensure the underlying ontology data products remain compliant, fresh, and trustworthy before they feed agent synthesis or executive workstations.

**Why this priority**: Constitution Principle IV mandates that data products have strict contracts and SLAs. If data quality degrades, downstream models and workstations must flag degraded status rather than presenting stale or invalid figures.

**Independent Test**: Navigate to the Data Platform & Operations Board; verify data products are listed with their freshness SLA status (e.g. `client_transactions` $< 5$ min, `partner_aggregates` $< 1$ hour); simulate a schema contract breach or freshness delay; verify that the product immediately transitions to amber/red `DEGRADED` status with an alert card; view the semantic metric catalog and inspect the upstream BigQuery and ontology function lineage.

**Acceptance Scenarios**:

1. **Given** the Data Quality board,  
   **When** reviewing active ontology products,  
   **Then** the board displays schema contract status, row counts, null-check scores, and latest ingestion timestamps for all products.
2. **Given** an ingestion pipeline exceeding its maximum freshness SLA threshold,  
   **When** the SLA monitor evaluates the product,  
   **Then** the board flags the product as `DEGRADED`, raises an alert card in the operations queue, and propagates a warning badge to any cockpit workstation consuming that product.
3. **Given** the Identity Cluster Conflict Inspector,  
   **When** cross-account entity resolution detects conflicting alias mappings or hardware fingerprint collisions across multiple partner trees,  
   **Then** the inspector presents the conflicting records with confidence weights and allows manual resolution or pseudonymized merge.
4. **Given** any metric in the semantic metric catalog,  
   **When** selecting the metric,  
   **Then** the canvas renders its end-to-end data lineage graph from source tables, through dbt transformation models and metric registry definitions, to consuming agent tools and cockpit widgets.

---

### Edge Cases

- **Streaming Synthesis Connection Drop**: When receiving real-time agent dossier synthesis via server-sent events, if the network connection drops or times out, the interface must gracefully buffer received text, present a non-intrusive reconnection banner, and resume from the last message sequence without freezing or clearing the dossier view.
- **Extreme High-Degree Graph Node ("Supernode")**: An entity in the AML or partner graph has $> 500$ first-degree connections (e.g. a centralized payment gateway or high-volume affiliate); the kinetic canvas must automatically apply hub suppression by clustering leaf nodes into collapsed summary badges to prevent DOM performance degradation and visual hairballs.
- **Unregistered / Hallucinated Metric Detected**: If an agent output text contains a numeric claim that lacks a matching entry in the deterministic metric registry, the Auditor Gate must mask the figure, render a caution badge, and flag the prompt output as unverified pursuant to Constitution Principle I.
- **Action Intent Token Expiration in Governed Action Shelf**: An investigator stages an action intent, but 15 minutes elapse before a second approver signs; the action modal must visually transition the token to `EXPIRED`, disable the commit trigger, and provide a single-click action to regenerate a fresh proposal token.
- **Concurrent Approvals on Dual-Approval Action**: Two compliance officers attempt to approve the exact same pending high-severity intent simultaneously; the transaction coordinator must accept the first approval, update the state to record approver 1, and present approver 2 with the confirmation button rather than throwing an unhandled race-condition error.
- **Total Synthesis Engine & LLM Outage**: During a complete failure of the Vertex AI / LLM gateway, all cockpit workstations must automatically enter Deterministic Fallback Mode, rendering pre-computed cached briefings and rule-based diagnostic cards clearly labelled with prominent `[REPLAY]` badges.
- **Narrow Viewport / Mobile Access**: If the workstation is accessed below the minimum desktop width ($1440$px), the interface must display an institutional warning banner stating that high-density tripartite investigation mode requires desktop resolution, while providing responsive single-column scrolling for read-only alert triage.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a tripartite Common Operational Picture (COP) layout consisting of a left Triage & Anomaly Inbox, center AI Copilot Dossier, right Kinetic Canvas / Explorer, and bottom-anchored Governed Action Shelf `[CONSTITUTION Principle II, IV]`.
- **FR-002**: System MUST render all user interface surfaces exclusively in high-contrast institutional light mode (`#ffffff` panel cards, `#f4f6f8` canvas background, slate-navy left rail `#1c2530`, text slate-900 `#0f172a`, border dividers `#e2e8f0`, sharp 0px radius) with zero dark-mode themes or toggles `[TARGET]`.
- **FR-003**: System MUST provide dedicated, role-tailored workstation views for 5 enterprise personas: Executive, AML Investigator, Partner Manager, Compliance Auditor, and Data Operations `[BRIEF, initial_plan.md §7]`.
- **FR-004**: System MUST render an interactive Deterministic Provenance Popover whenever a user hovers or clicks on any scalar metric across all cards, charts, and dossiers, displaying `metric_id`, `definition_version`, `as_of_timestamp`, `computation_source`, and `owner_role` `[CONSTITUTION Principle I, V]`.
- **FR-005**: System MUST enforce the Metric Auditor Gate across all agent-synthesized narratives, automatically intercepting and blocking any numeric assertion that is not traced to a registered ontology metric or tool return `[CONSTITUTION Principle I]`.
- **FR-006**: System MUST automatically display a prominent `[REPLAY]` or `[CACHED]` status badge on any card, briefing, or dossier populated with fallback data during an underlying service outage `[CONSTITUTION Principle VIII]`.
- **FR-007**: Executive Workstation MUST display an auto-pushed Morning Briefing synthesizing operational events across 4 horizons: Competitive, Partner, Client, and Financial `[BRIEF, initial_plan_v2.md §6]`.
- **FR-008**: Executive Workstation MUST render an interactive 4-domain causal DAG with distinct visual styling for verified causal vectors (passing refuter gates) versus unverified correlations (failing refuter gates) `[CONSTITUTION Principle III]`.
- **FR-009**: Executive Workstation MUST provide an interactive What-If Shock Slider executing parametric propagation across the cached structural causal model within 200 ms without full offline DAG refitting `[CONSTITUTION Principle VII]`.
- **FR-010**: Executive Workstation MUST render forecast attribution waterfalls where total positive and negative attribution components sum to exactly $100\% \pm 0.01\%$ `[BRIEF, initial_plan.md §7]`.
- **FR-011**: AML Workstation MUST present a prioritized alert triage queue sorting alerts by composite AML hazard score, discrepancy multiplier, and syndicate linkage `[BRIEF, docs/brief/fraud.md]`.
- **FR-012**: AML Workstation MUST render a one-screen unified entity dossier aggregating KYC/KYB records, deposit-to-income discrepancy metrics, pseudonymized identity cluster keys (`tok_id_cluster_<hex16>`), and transaction histories `[CONSTITUTION Principle IV]`.
- **FR-013**: AML Workstation MUST render an interactive kinetic network graph displaying multi-hop entity relationships, transaction flows, and matched timing edges with dynamic hub suppression for high-degree nodes ($> 100$ connections) `[TARGET]`.
- **FR-014**: AML Workstation MUST generate structured, regulator-ready SAR (Suspicious Activity Report) drafts pre-populated with evidence citations, transaction amounts, and syndicate timelines `[BRIEF, initial_plan.md §7]`.
- **FR-015**: Partner Workstation MUST render a Churn Radar scatter plot visualizing partners across 30-day realized trading volume versus churn hazard probability with optimal 14-day intervention countdowns `[BRIEF, docs/brief/monitoring.md]`.
- **FR-016**: Partner Workstation MUST visualize partner referral trees with automated detection and highlighting of opposite-trading / mirror-trading rings `[BRIEF, docs/brief/fraud.md]`.
- **FR-017**: Partner Workstation MUST provide governed retention playbook recommendations, enforcing fast-path approval for deals $\le \$2,500$ and routing higher-impact deals to executive approval `[TARGET]`.
- **FR-018**: Compliance Workstation MUST render an interactive timeline explorer of the monotonic decision ledger displaying atomic sequence numbers (`ledger_seq = 1, 2, 3...`) `[CONSTITUTION Principle II]`.
- **FR-019**: Compliance Workstation MUST provide an interactive cryptographic hash chain verification tool that visually walks the sequence and verifies that $H_i = \text{SHA-256}(H_{i-1} \parallel \text{seq}_i \parallel \text{payload}_i)$ `[CONSTITUTION Principle II]`.
- **FR-020**: Compliance Workstation MUST display periodic WORM checkpoint anchors, including Cloud Storage Object Retention Lock proofs, expiration timestamps, and compliance lock status `[CONSTITUTION Principle II]`.
- **FR-021**: Compliance Workstation MUST inspect Four-Eyes approval records, verifying two distinct authenticated officer signatures and documented review notes for all High-severity executions `[CONSTITUTION Principle II]`.
- **FR-022**: Data Operations Workstation MUST display real-time Data Quality (DQ) boards, schema contract breach alerts, ingestion freshness SLA monitors, and semantic metric catalog lineage topologies `[CONSTITUTION Principle IV]`.
- **FR-023**: System MUST host a Governed Action Shelf implementing the Two-Phase Commit protocol for all agent mutation proposals, displaying staged `ActionIntentToken` review cards with Cloud KMS asymmetric signature validation `[CONSTITUTION Principle II]`.
- **FR-024**: System MUST enforce role-based access control (RBAC) across all workstation tabs and action triggers, ensuring operators can only view data markings and execute mutations permitted by their authenticated identity claims `[CONSTITUTION Principle IV]`.

---

### Key Entities

- **`WorkstationViewSession`**: Represents the active operator session, capturing authenticated user ID, assigned role (Executive, AML Investigator, Partner Manager, Compliance Auditor, Data Engineer), active workstation tab, and applied triage filters.
- **`MorningBriefingDossier`**: The synthesized executive morning report containing generation timestamp, horizon summaries (Competitive, Partner, Client, Financial), ranked operational risks, and market opportunity recommendations.
- **`CausalDAGGraph`**: The interactive network representation of the business causal model, containing nodes (business metrics, external shocks), directed edges, refuter validation test results, and confidence scores.
- **`EntityInvestigationDossier`**: The unified one-screen AML investigation record aggregating declared KYC/KYB data, deposit-to-income ratios, pseudonymized identity cluster keys, device fingerprints, and fiat/crypto transaction histories.
- **`KineticNetworkGraph`**: The graph model for entity relationships and transaction flows, containing node models (accounts, payment agents, IP/device nodes), edge models (transactions, matched timing links), and cluster collapse state.
- **`SARDraftDocument`**: The structured regulatory filing document pre-populated with case summary, subject particulars, narrative breakdown, evidence citations, and investigator sign-off metadata.
- **`ChurnRadarScatter`**: The analytical dataset driving partner retention analysis, capturing partner IDs, 30-day trading volume, churn hazard probability, decay indicators, and optimal intervention window countdowns.
- **`GovernedActionCard`**: The UI presentation model for an in-flight `ActionIntentToken`, displaying intent ID, action type, target entity, financial/operational parameters, severity level, KMS signature verification status, approval state machine progress, and expiration countdown.
- **`ProvenanceMetadata`**: The deterministic metadata attached to every rendered scalar metric, containing metric ID, ontology semantic definition version, as-of calculation timestamp, computation engine origin, and steward role.
- **`DataProductSLAStatus`**: The operational monitoring record capturing data product name, schema contract status, row count, null-check score, ingestion timestamp, freshness SLA target, and degraded status badge.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of rendered screens strictly comply with the institutional light-mode design specification (`#ffffff` panel cards, `#f4f6f8` ground, `#1c2530` slate-navy rail, 0px border radius) with zero dark-mode themes available `[TARGET]`.
- **SC-002**: 100% of quantitative metric values rendered across all 5 workstations provide an instant Provenance Popover showing metric ID, version, calculation timestamp, and owner role within $< 50$ ms of user hover/click `[CONSTITUTION Principle I, V]`.
- **SC-003**: 100% of agent-synthesized narrative figures pass the Metric Auditor Gate; zero unverified or hallucinated numbers are presented to operators `[CONSTITUTION Principle I]`.
- **SC-004**: During simulated LLM or synthesis gateway outages, 100% of impacted views gracefully degrade to cached snapshots stamped with prominent `[REPLAY]` or `[CACHED]` status badges without application crashes `[CONSTITUTION Principle VIII]`.
- **SC-005**: Interactive What-If Shock Slider updates forward projections and attribution waterfall within $< 200$ ms via parametric propagation `[CONSTITUTION Principle VII]`.
- **SC-006**: 100% of forecast attribution waterfall components mathematically sum to $100\% \pm 0.01\%$ `[TARGET]`.
- **SC-007**: Kinetic network graph successfully renders clusters up to 1,000 entities while maintaining $> 30$ FPS canvas interaction performance through automated hub suppression `[TARGET]`.
- **SC-008**: 100% of High-severity mutation actions staged in the Governed Action Shelf enforce the Two-Phase Commit workflow and block execution until two distinct authenticated officer approvals are recorded `[CONSTITUTION Principle II]`.
- **SC-009**: Compliance & Audit Explorer completes end-to-end cryptographic hash chain verification across 10,000 sequential ledger records in $< 1.0$ second with visual verification feedback `[CONSTITUTION Principle II]`.
- **SC-010**: All interactive workstation views achieve WCAG 2.2 AA accessibility compliance for color contrast ratios ($\ge 4.5:1$ for normal text, $\ge 3:1$ for graphical objects and large text) and full keyboard navigation support `[TARGET]`.

---

## Assumptions

- **Institutional Display Environment**: Operators access the system using high-resolution desktop or laptop displays (minimum recommended resolution $1440 \times 900$, optimized for $1920 \times 1080$ and $2560 \times 1440$). Ultra-dense multi-column tripartite investigation workflows are targeted at desktop operator workstations rather than small-screen mobile devices.
- **Identity Provider Integration**: User authentication, session management, and role-based access control (RBAC) claims are issued by an enterprise Identity Provider (IdP) via secure HTTP cookies or bearer tokens. The workstation trusts verified IdP claims for approver role determination.
- **Server-Sent Events / WebSocket Support**: The operator's network environment supports persistent streaming connections (HTTP Server-Sent Events or WebSockets) for real-time agent dossier token streaming and live triage alert push notifications.
- **Simulated Core Execution**: Action execution commands triggered from the Governed Action Shelf commit against the simulated core write-back sink established in Feature 011, providing realistic operational receipts without mutating live external banking APIs.
- **Technology-Agnostic Client Contract**: The workstation specification defines visual design tokens, interaction flows, state machines, and latency requirements technology-agnostically, preserving open architectural decisions ADR-009 (frontend framework) and ADR-014 (API protocol).
