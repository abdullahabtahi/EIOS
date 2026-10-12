# Quickstart Validation Guide: Institutional Operator Cockpit (016-cockpit-frontend)

**Branch**: `016-cockpit-frontend` | **Date**: 2026-10-10 | **Feature Spec**: [spec.md](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/specs/016-cockpit-frontend/spec.md)

This quickstart guide provides runnable validation scenarios to prove that the Institutional Operator Cockpit functions as a production-grade, connected Common Operational Picture (COP) integrating all 15 platform subsystems (Features 001–015) with QuantumBlack Institutional Light Mode design rigor and Google Cloud Engineer quality standards.

---

## 1. Prerequisites & Full-Stack Environment Setup

Ensure Python ($\ge 3.11$) virtual environment and Node.js ($\ge 20.0$) dependencies are ready:

### 1.1 Python Backend Cockpit Presentation Gateway

```bash
cd "/Users/abdullahabtahi/Real-Time Enterprise Intelligence Agent/FEIOS"
source .venv/bin/activate

# Verify backend cockpit contracts and unit tests pass (48/48)
pytest tests/cockpit/ -v

# Start the Python Cockpit API Gateway (port 8000)
python -m eios.cockpit.server --port 8000
```

### 1.2 Next.js Full-Stack Frontend Client

In a separate terminal:

```bash
cd "/Users/abdullahabtahi/Real-Time Enterprise Intelligence Agent/FEIOS/web-prototype"
npm install

# Start Next.js development server (port 3000)
npm run dev
# Cockpit workstation is mounted at: http://localhost:3000/cockpit
```

---

## 2. Full-Stack Validation Scenarios

### Scenario 1: Universal Tripartite Shell & QuantumBlack Institutional Light Mode (FR-001, FR-002, SC-005)

1. **Action**: Open `http://localhost:3000/cockpit` in a desktop browser ($1440 \times 900$).
2. **Expected Outcome**:
   - The interface renders the tripartite layout: Left Triage Rail ($300\text{px}$), Center Copilot Dossier ($560\text{px}$), Right Kinetic Horizon Canvas (remaining viewport), Bottom Docked Governed Action Shelf, and Top Copilot Command Bar.
   - The palette strictly reflects Institutional Light Mode: `#ffffff` white panel cards, `#f8fafc` canvas ground, `#0f172a` slate-navy primary headers, crisp `1px` `#e2e8f0` borders, and sharp radii.
   - Zero dark-mode toggles or dark themes exist anywhere in the interface.

---

### Scenario 2: Conversational Copilot Command Bar & Auditor Gate (FR-021, Feature 007)

1. **Action**: Click the top `<CopilotCommandBar>` or press `Cmd+K`.
2. **Submit Grounded Query**:
   - Enter: "What is our 30-day net deposit turnover for partner P-882?"
   - **Verification**: The system routes the query through `OMCPServer.call_tool("get_metric")`. The Metric Auditor Gate analyzes the response, verifies that 100% of numerical figures anchor to tool traces, and displays the response with green provenance citations.
3. **Submit Ungrounded Query**:
   - Enter a query prompting speculative figures (e.g., "Estimate potential next-quarter revenue without tools").
   - **Verification**: The Metric Auditor Gate flags unanchored figures, blocks output generation, and displays: "Insufficient data to substantiate figure; LLMs never compute business metrics" (Constitution Principle I & III).

---

### Scenario 3: Executive Workstation Morning Briefing & Sub-200ms What-If Simulation (FR-006, FR-007, FR-008, SC-003, Feature 006)

1. **Action**: Select the **Executive Cockpit** persona.
2. **Inspect Center Dossier**:
   - Verify the Morning Briefing displays 4 horizons: Competitive, Partner, Client, and Financial.
   - Hover over any metric (e.g. `Net Revenue $4.82M`); verify that an accessible Popover opens displaying Metric ID, semantic definition version, calculation engine, and owner role.
3. **Inspect Right Kinetic Canvas**:
   - Verify the 4-domain Causal DAG displays verified causal edges in solid emerald green (with refuter $p > 0.05$) and unverified edges in dashed amber labeled "correlation detected; insufficient evidence for causation" (Principle III).
4. **Manipulate What-If Shock Slider**:
   - Drag the "Competitor Commission Shock" slider from $+0\text{ bps}$ to $+200\text{ bps}$.
   - **Verification**: Forward EBITDA projections and the waterfall attribution chart update in $< 200\text{ms}$. Verify that the waterfall components sum to exactly $100.0\% \pm 0.01\%$.

---

### Scenario 4: AML Investigator Workstation, CGNAT Hub Suppression & Flywheel Feedback (FR-010, FR-011, FR-012, FR-022, Features 010 & 014)

1. **Action**: Switch persona to **AML Investigator Workstation**.
2. **Inspect Left Triage Rail**:
   - Verify that raw transaction alerts are collapsed into $\le 50$ prioritized investigation clusters ranked by priority score.
3. **Select High-Priority Case**:
   - Select case `CASE-2026-AML-8921` (rapid micro-turnover round trip).
   - Verify the center dossier presents a unified single-screen evidence file (KYC status, turnover ratio, transaction velocity, SAR draft document).
4. **Inspect Relational Graph Canvas**:
   - Toggle "CGNAT Hub Suppression" on/off.
   - Verify that high-degree shared IP nodes ($\text{degree} \ge 15$) are suppressed, preventing false-positive account merges.
5. **Submit Flywheel Feedback**:
   - In the SAR Draft narrative editor, edit a paragraph and click "Submit Flywheel Annotation".
   - **Verification**: An event is dispatched to `/api/cockpit/flywheel/feedback`, recording the operator revision into the closed-loop Decision Outcomes Ledger (Feature 014).

---

### Scenario 5: Partner Manager Workstation & Mirror Trading Radar (FR-014, FR-015, FR-016, Features 008 & 009)

1. **Action**: Switch persona to **Partner Manager Workstation**.
2. **Inspect Churn Hazard Radar**:
   - Verify the scatter plot graphs partners across $P(\text{churn})$ vs. Value at Risk.
   - Click a decaying partner node; verify that the center dossier displays change-point decay indicators and recommended retention playbooks.
3. **Inspect 3-Tier Referral Tree & Fraud Canvas**:
   - Verify the 3-tier sub-affiliate tree renders master and sub-broker commission splits.
   - Inspect flagged mirror trading pairs; verify timing co-occurrence percentage ($\ge 85\%$) and net commission extracted are highlighted.

---

### Scenario 6: Compliance Ledger Timeline & Data Operations Disaster Recovery Board (FR-017, FR-020, FR-023, Features 011, 013 & 015)

1. **Action**: Switch persona to **Compliance Auditor & Operations**.
2. **Inspect Decision Ledger**:
   - Verify the immutable ledger timeline lists consecutive sequence numbers (`ledger_seq = 1, 2, 3...`).
   - Click "Verify Chain Continuity"; verify the SHA-256 hash chain verification badge displays `VALID` with WORM mode locked.
3. **Inspect Data Platform Operations Board**:
   - Verify live streaming freshness latency indicators ($< 30\text{s}$) across all 6 data products.
   - Verify DLQ quarantine queue depth and 10-SLO continuous error budget status cards.
   - Verify Red-Line test gates (RL-1..RL-7) show PASS status.
   - Inspect Disaster Recovery runbook proofs: verify Cloud KMS key rotation status (`ACTIVE_ROTATED`) and backup checkpoint hash match Feature 015 proofs.

---

### Scenario 7: Governed Action Shelf & Two-Phase Four-Eyes Authorization (FR-018, FR-019, SC-004, Feature 011)

1. **Action**: In the AML or Partner workstation, click "Stage Hold Proposal" or "Freeze Commission".
2. **Verify Staged State**:
   - The proposal appears in the bottom docked `<GovernedActionShelf>` in `STAGED` status with an ECDSA P-256 Cloud KMS signature badge and a 15-minute expiration countdown.
3. **Attempt Execution (Single Officer)**:
   - Click "Commit Action".
   - **Verification**: Because the action is High severity, execution is blocked. An accessible Four-Eyes Authorization Modal opens requiring a second distinct officer ID and cryptographic credential.
4. **Simulate Second Officer Approval**:
   - Enter Officer 2 credentials (`officer_id: compliance_lead_44`) and click "Authorize & Commit".
   - **Verification**: The Action Intent transitions to `COMMITTED`, logs an immutable entry to the Decision Ledger via `SimulatedWriteBackSink`, and clears from the pending tray. Zero autonomous execution occurs without human sign-off (Principle II).

---

### Scenario 8: Outage Simulation & Deterministic Replay Badging (FR-005, SC-002, Principle VIII)

1. **Action**: In the top header bar, toggle the "Simulate Upstream Outage" debug switch (or stop the Python backend server).
2. **Expected Outcome**:
   - Center dossier narratives transition to cached domain snapshots generated by `eios.cockpit.fallback`.
   - Every cached card displays an unambiguous amber `[REPLAY]` badge: `[REPLAY] Cached as of 2026-10-10 08:00:00 UTC` (Principle VIII).
   - Numerical provenance badges and What-If slider propagation continue to calculate deterministically without unverified filler text.

---

## 3. Automated Verification Commands

Run full-stack verification across both backend Python contract suites and frontend Next.js component suites:

```bash
# 1. Backend Python Contract & Cockpit Service Verification (48 tests)
cd "/Users/abdullahabtahi/Real-Time Enterprise Intelligence Agent/FEIOS"
source .venv/bin/activate
pytest tests/cockpit/ -v

# 2. Frontend Component, Contract Schema & Invariant Verification
cd "/Users/abdullahabtahi/Real-Time Enterprise Intelligence Agent/FEIOS/web-prototype"
npm test

# 3. TypeScript Strict Type Verification
npx tsc --noEmit

# 4. ESLint Verification
npm run lint
```
