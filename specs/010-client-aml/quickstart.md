# Quickstart Validation Guide: Client Fraud Sentinel / AML Transaction Monitoring (Module A / Slice S4)

**Feature**: `specs/010-client-aml/` (Module A / Slice S4)  
**Standard**: QuantumBlack Horizon Architecture × Palantir Foundry Kinetic Ontology  
**Authoritative References**: `docs/brief/monitoring.md` `[BRIEF monitoring]`, `initial_plan.md` §5.4, `docs/models_and_evals.md` §2

---

## 1. Prerequisites & Environment

Ensure the virtual environment is active and dependencies are installed:

```bash
cd FEIOS
source .venv/bin/activate
export PYTHONPATH=src:$PYTHONPATH
```

Verify that the foundational L1 data products are hydrated in the DuckDB hot state (`transactions_aml`, `trading_activity`, `device_network_graph`, `compliance_cases`).

---

## 2. Validation Scenarios

### Scenario 1: Pre-Registered Naive Baseline Evaluation Gate (Constitution Principle VI)
Run the blocking evaluation test comparing the supervised alert triage model and round-trip detector against the pre-registered naive rule baseline across sealed seeds:

```bash
pytest tests/aml/test_aml_eval.py -v
```

**Expected Outcome**:
- Naive static threshold baseline ("deposit $> \$10,000$ or velocity $> 3$") achieves baseline PR-AUC (e.g. ~0.50).
- Supervised Alert Triage Scorer achieves PR-AUC $\ge \text{Baseline} + 0.15$ (e.g. $\ge 0.65$) `[CONSTITUTION Principle VI]`.
- Top-50 prioritized alerts capture $\ge 90\%$ of planted true positive laundering cases from 2,000 weekly alerts `[BRIEF monitoring]`.
- Hard-negative legitimate high-volume traders achieve $\ge 30\%$ relative reduction in false alarms vs. naive rules `[TARGET]`.

---

### Scenario 2: Batch AML Surveillance Pipeline
Execute the end-to-end client AML surveillance pipeline over synthetic transactions and account histories:

```bash
python scripts/run_client_aml_pipeline.py --as-of 2026-10-07 --seed 42
```

**Expected Outcome**:
- Ingests ~2,000 transaction alerts, evaluates peer cohorts, and computes calibrated triage risk scores.
- Scans account lifecycles and detects rapid round-trip structuring (deposit $\to$ 10 min micro-trading $\to$ withdrawal within 72h of KYC approval `[BRIEF monitoring]`).
- Traverses the bipartite entity graph with hub suppression, isolating coordinated mule rings without false-merging public Wi-Fi gateways.
- Populates DuckDB hot-state tables: `aml_alert_scores`, `aml_roundtrip_events`, `aml_mule_rings`, and `aml_case_dossiers`.
- Execution completes in $< 20\text{s}$ for 2,000 alerts `[TARGET]`.

---

### Scenario 3: Real-Time Pre-Withdrawal Fraud Intervention
Validate sub-2.0s real-time risk checks on inbound withdrawal requests:

```bash
python scripts/test_withdrawal_sentinel.py --client-id C-AML-ROUNDTRIP-01 --amount 495.00
```

**Expected Outcome**:
- Pre-withdrawal sentinel evaluates client recent events in $< 2.0\text{s}$ (p95) `[TARGET]`.
- Detects acute micro-P&L round-trip risk and flags the transaction.
- Emits a Cloud KMS ECDSA P-256 signed `ActionIntentToken` proposal for `HoldWithdrawal` in `PENDING` status.
- Verification confirms zero direct balance deduction occurred without human approval `[CONSTITUTION Principle II]`.

---

### Scenario 4: OMCP Tool Surface Verification
Verify the canonical AML OMCP tool handlers via unit and integration tests:

```bash
pytest tests/ontology/test_omcp_client_aml_tools.py -v
```

1. **`get_client_aml_dossier(client_id="C-AML-ROUNDTRIP-01")`**: Returns the complete investigation pack compiling 5+ source systems with 100% cited metrics.
2. **`get_mule_ring_graph(client_id="C-AML-MULE-01")`**: Returns the isolated mule cluster with plain-language network explanations and hub suppression metadata.
3. **`get_roundtrip_structuring_alerts(window_hours=72)`**: Returns all active micro-P&L round-trip structuring anomalies.
4. **`check_withdrawal_risk(withdrawal_id="W-1001", client_id="C-AML-ROUNDTRIP-01", amount=500.0)`**: Executes real-time pre-withdrawal evaluation.
5. **`generate_sar_draft(case_id="CASE-AML-01", template_jurisdiction="US_FINCEN")`**: Generates a regulator-ready SAR narrative passing the Metric Auditor Gate and normalizing statutory references (`31 CFR 1010` `[CONSTITUTION Principle VII]`).

All response payloads validate strictly against contracts in [`contracts/`](contracts/).
