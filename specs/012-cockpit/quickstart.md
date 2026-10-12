# Quickstart Validation Guide: Executive Cockpit & Operator Workstations (012-cockpit)

**Feature**: Executive Cockpit & Operator Workstations (F11 / Slice S6)  
**Spec**: [`specs/012-cockpit/spec.md`](spec.md)  
**Data Model**: [`specs/012-cockpit/data-model.md`](data-model.md)  
**Contracts**: [`specs/012-cockpit/contracts/`](contracts/)  
**Status**: Ready for Implementation  

---

## 1. Prerequisites & Environment Setup

Verify the Python 3.11+ / uv virtual environment and existing feature test baselines:

```bash
# Verify active environment and dependencies
cd "/Users/abdullahabtahi/Real-Time Enterprise Intelligence Agent/FEIOS"
uv run pytest tests/unit/tools/decisions/ -q
```

---

## 2. End-to-End Validation Scenarios

### Scenario 1: Institutional Light-Mode Token Validation & Palette Compliance
**Objective**: Mathematically prove zero dark-mode leaks and institutional light-mode token compliance (Palantir Solution Designer $\times$ QBDS).

```bash
# Run token compliance check against design tokens
uv run pytest tests/cockpit/test_design_tokens.py -v
```
- **Expected Outcome**:
  - `surface_ground` resolves to `#f4f6f8`
  - `surface_card` resolves to `#ffffff`
  - `surface_rail` resolves to `#1c2530`
  - `radius_base` resolves to `0px`
  - Contrast ratio between text (`#0f172a`) and surface (`#ffffff`) is $\ge 12.5:1$ (exceeding WCAG 2.2 AA $4.5:1$)
  - Dark-mode toggle presence assertion returns `False`

---

### Scenario 2: Instant Deterministic Metric Provenance Popovers ($< 50$ ms)
**Objective**: Verify that hovering or clicking any scalar metric returns full provenance without LLM hallucination.

```bash
# Validate provenance resolver latency and schema binding
uv run pytest tests/cockpit/test_metric_provenance.py -v
```
- **Expected Outcome**:
  - Resolution latency across 1,000 queries is $< 50$ ms p95
  - Returned payload strictly adheres to [`provenance-metadata.schema.json`](contracts/provenance-metadata.schema.json)
  - Unregistered numeric assertions trigger immediate rejection by the `MetricAuditorGate`

---

### Scenario 3: Executive What-If Shock Slider & 100% Additive Attribution ($< 200$ ms)
**Objective**: Verify that dragging the scenario shock slider executes parametric propagation across cached SCM coefficients without full batch DAG refitting.

```bash
# Validate scenario simulation parametric propagation and attribution sum
uv run pytest tests/cockpit/test_executive_what_if.py -v
```
- **Expected Outcome**:
  - Parametric propagation response latency is $< 200$ ms
  - Downstream 30/60/90-day EBITDA and churn probability updates reflect structural coefficients
  - Sum of attribution components equals $100.00\% \pm 0.01\%$

---

### Scenario 4: AML One-Screen Dossier & Dynamic Graph Hub Suppression
**Objective**: Verify that investigating high-risk account CR84920 loads the unified dossier and suppresses supernode graph hairballs.

```bash
# Validate AML dossier assembly and graph layout performance
uv run pytest tests/cockpit/test_aml_workstation.py -v
```
- **Expected Outcome**:
  - Unified dossier aggregates KYC source-of-wealth, deposit discrepancy ($1,600\%$), and `tok_id_cluster_<hex16>` in $< 150$ ms
  - Kinetic network graph activates hub suppression on payment agents with degree $> 100$, grouping leaf nodes into meta-badges
  - Canvas layout computation sustains $> 30$ FPS equivalent

---

### Scenario 5: Governed Two-Phase Commit Action Staging & Four-Eyes Modal
**Objective**: Verify that staging a `HoldWithdrawal` action intent generates a KMS-signed card requiring dual distinct human approvals.

```bash
# Validate 2PC action shelf state progression and Four-Eyes enforcement
uv run pytest tests/cockpit/test_governed_action_shelf.py -v
```
- **Expected Outcome**:
  - Action card renders in `PENDING_APPROVAL` with `requires_four_eyes = True`
  - First approver sign-off records signature and maintains `PENDING` state
  - Second distinct approver sign-off unlocks transition to `APPROVED`
  - Single-user double-sign attempt is rejected with authorization error

---

### Scenario 6: Deterministic Replay Fallback under Simulated LLM Outage
**Objective**: Verify that simulated synthesis engine failure automatically triggers cached replay mode with prominent `[REPLAY]` badges.

```bash
# Simulate gateway timeout and verify fallback engine behavior
uv run pytest tests/cockpit/test_cockpit_fallback.py -v
```
- **Expected Outcome**:
  - Synthetic 504 Gateway Timeout or LLM disconnect does not crash workstation
  - Workstation immediately serves verified cached snapshot with amber `[REPLAY]` status badge
  - Zero hallucinated or invented text emitted
