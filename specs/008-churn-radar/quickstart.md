# Quickstart & Live Demo Validation Guide: Partner Churn Radar

**Branch**: `008-churn-radar` | **Date**: 2026-10-07  
**Standard**: QuantumBlack Horizon Architecture × Palantir Foundry Live Demo Standard  
**Companion Docs**: `specs/008-churn-radar/spec.md`, `specs/008-churn-radar/plan.md`

---

## 1. Overview & Demo Objectives

This guide provides end-to-end instructions for running the **Partner Churn Radar (Module C / Slice S2)** in both automated evaluation mode and live interactive demo mode. 

During the live demonstration, the system proves:
1. **Eval-First Superiority**: The discrete-time hazard model outperforms the baseline rules engine by $\ge 0.10$ PR-AUC on sealed holdout seeds.
2. **Value-at-Risk Operational Queuing**: Partners are prioritized by preserved revenue rather than raw risk scores.
3. **Zero False Alarms**: The seasonality-adjusted change-point detector filters out seasonal holiday dips (`P-HARD-NEG-VACATION`).
4. **Systemic Cohort Detection**: Synchronized regional disengagements (`P-COHORT-SEA-CLUSTER`) trigger unified cohort alerts.
5. **GenAI Pattern Discovery**: Unstructured support tickets are clustered into novel disengagement hypotheses with structured Pydantic egress.
6. **Governed Action & Causal Flywheel**: Retention interventions emit KMS-signed `ActionIntentToken` proposals, closing the learning loop via Doubly Robust AIPW.

---

## 2. Prerequisites & Environment Setup

Ensure the active Python 3.11 environment is initialized with all core dependencies:

```bash
cd FEIOS
pip install -e .
pip install lifelines>=0.29.0 duckdb>=1.1.0 scipy>=1.13.0 cryptography>=42.0.0
```

Rehydrate synthetic partner data and initialize the in-process DuckDB Hot State:

```bash
# Seed synthetic L1 Data Products (DP6 - DP12) into hot state
python -m eios.foundry.cli --seed dev --universe 1000
```

---

## 3. Validation Scenarios

### Scenario 1: Baseline Evaluation Gate (Eval-First CI Gate)
Run the automated evaluation harness to verify that the discrete-time hazard model strictly beats the pre-registered "no login > 14 days" baseline on a sealed holdout seed.

**Command**:
```bash
pytest tests/churn/test_churn_radar_eval.py -v -k "test_hazard_beats_baseline"
```

**Expected Console Output**:
```text
============================= test session starts ==============================
tests/churn/test_churn_radar_eval.py::test_hazard_beats_baseline PASSED    [100%]

--- EVALUATION REPORT: PARTNER CHURN RADAR ---
Baseline ("No login > 14 days"):   PR-AUC = 0.642 | Median Lead Time = 11 days
Challenger (Discrete Hazard):       PR-AUC = 0.814 | Median Lead Time = 19 days
Delta Commitment [TARGET]:          +0.172 PR-AUC  (Commitment: >= +0.10) -> PASS
Lead Time Gain [TARGET]:            +8 days        (Commitment: >= +7 days) -> PASS
Brier Calibration Score:            0.088          (Commitment: <= 0.12) -> PASS
============================== 1 passed in 4.12s ===============================
```

---

### Scenario 2: Live Persona Demo (The Three Golden Personas)
Execute the batch scoring pipeline in demo mode to inspect the three canonical personas.

**Command**:
```bash
python scripts/run_churn_pipeline.py --demo-mode
```

**Expected Live Output**:
```text
================================================================================
EIOS PARTNER CHURN RADAR - OPERATIONAL COCKPIT (SLICE S2)
================================================================================

[QUEUE #1: HIGH VALUE-AT-RISK RETENTION QUEUE]
Rank  Partner ID           Tier         Value-at-Risk  Hazard 30d  Priority Score  Status
1     P-CHURN-DRIFT        VIP_MASTER   $45,000        0.76        $34,200         ACTION REQUIRED
2     P-9921               TIER_1       $28,000        0.65        $18,200         ACTION REQUIRED
3     P-4012               TIER_2       $12,000        0.82        $9,840          ACTION REQUIRED

>>> INSPECTING TOP PARTNER: P-CHURN-DRIFT
    - Signal Breakdown:
      * BEHAVIORAL:   Login frequency velocity down -42% WoW (DP9:partner_engagement_signals)
      * COMPETITIVE:  Ticket #8492 mentions rival broker revshare (DP10:partner_comms)
      * FINANCIAL:    Trailing 30d commission declined -18% (DP8:commission_ledger)
    - Optimal Window: OPTIMAL INTERVENTION WINDOW (Lead time: 21 days remaining)
    - Explanation:    "VIP Partner P-CHURN-DRIFT exhibits acute disengagement risk driven
                      by 42% login decay and active competitor poaching inquiries."

[QUEUE #2: SEASONALITY FILTER VERIFICATION (ZERO FALSE ALARMS)]
Target Partner: P-HARD-NEG-VACATION (Tier-2 European Affiliate)
- Raw Observed Volume: 0 logins, 0 clicks for 14 days (August holiday pause)
- Seasonality-Adjusted CUSUM Filter: HOLIDAY DIP DETECTED (Trading calendar masked)
- Risk Classification: LOW (Hazard = 0.12, Alert SUPPRESSED)
- Result: ZERO FALSE ALARM CONFIRMED.

[QUEUE #3: SYSTEMIC REGIONAL COHORT ALERTS]
Alert ID: COHORT-SEA-8821 | Region: IDN_MYS | Partners: 15
- Aggregate Value-at-Risk: $180,000 USD
- Common Driver: Regional Competitor Zero-Spread Campaign (Permutation p-value: 0.0004)
- Recommended Action: Launch Regional Master Retention Playbook
================================================================================
```

---

### Scenario 3: GenAI Emerging Pattern Discovery
Execute the `PatternDiscoverySpecialist` over unstructured support tickets to demonstrate novel pattern discovery (Hackathon "Blow Our Minds" feature).

**Command**:
```bash
python scripts/test_churn_pattern_discovery.py --region IDN_MYS
```

**Expected Console Output**:
```json
{
  "theme_id": "DISCOVERY-THEME-004",
  "title": "MT5 WebSocket Rate Limit Frustration",
  "affected_partner_count": 14,
  "signal_families_implicated": ["COMMUNICATION", "COMPETITIVE"],
  "confidence_score": 0.94,
  "supporting_ticket_ids": ["TICK-8812", "TICK-8845", "TICK-8901"],
  "plain_language_summary": "Partners managing algorithmic trading clients report repeated MT5 WebSocket connection drops during Asian market open. Competitor XM is actively referenced as offering dedicated low-latency gateway connections.",
  "actionable_remediation": "Deploy regional MT5 edge proxy in Singapore; launch dedicated CSM outreach with API latency SLA guarantee.",
  "auditor_status": "PASSED (0 metric hallucinations)"
}
```

---

### Scenario 4: Governed Action Intent & The Closed-Loop Flywheel
Propose a retention playbook for `P-CHURN-DRIFT`, verify cryptographic signing, and execute a simulated Doubly Robust AIPW recalibration.

**Command**:
```bash
python scripts/test_retention_intent.py --partner-id P-CHURN-DRIFT --playbook VIP_COMMISSION_BOOST --budget 5000
```

**Expected Console Output**:
```text
[GOVERNANCE] Action Proposal Submitted via OMCP propose_action:
- Action Type:       LaunchRetentionPlaybook
- Target Partner:    P-CHURN-DRIFT
- Staged Playbook:   VIP_COMMISSION_BOOST ($5,000 budget)
- Propensity e(X):   0.88 (stamped for AIPW counterfactual tracking)
- Intent Status:     PENDING (Awaiting Human Four-Eyes Authorization)
- Nonce:             0a8f7b3c4d2e1f9a
- KMS Key ID:        projects/eios/locations/global/keyRings/omcp/cryptoKeys/action-signer:1
- ECDSA Signature:   MEQCID9x1...Base64...SignedToken (Cryptographically Verified)

[SIMULATED FLYWHEEL RECALIBRATION]
- Fetching 100 logged outcomes from decision_outcomes_ledger...
- Running Doubly Robust AIPW Estimator vs. Naive Observational Average:
  * Naive Observed ATE:   -$4,200 USD (Biased by selection confounding)
  * Doubly Robust AIPW:   +$14,800 USD (Statistically significant positive uplift, p=0.002)
- Recalibrated Playbook Weight for VIP_COMMISSION_BOOST: 1.0 -> 1.35
[FLYWHEEL CLOSED-LOOP COMPLETE]
```
