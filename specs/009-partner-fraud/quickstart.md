# Quickstart Validation Guide: Partner & Affiliate Fraud Sentinel (Module B / Slice S3)

**Feature**: `specs/009-partner-fraud/` (Module B / Slice S3)  
**Standard**: QuantumBlack Horizon Architecture × Palantir Foundry Kinetic Ontology  
**Authoritative References**: `docs/brief/fraud` `[BRIEF fraud]`, `initial_plan.md` §5.3

---

## 1. Prerequisites & Environment

Ensure the virtual environment is active and dependencies are installed:

```bash
cd FEIOS
source .venv/bin/activate
export PYTHONPATH=src:$PYTHONPATH
```

Verify that the foundational L1 data products are hydrated in the DuckDB hot state (`partner_360`, `partner_network`, `trading_activity`, `commission_ledger`, `transactions_aml`, `clickstream`).

---

## 2. Validation Scenarios

### Scenario 1: Pre-Registered Naive Baseline Gate (Constitution Principle VI)
Run the blocking evaluation test comparing the statistical pair collusion detector against the naive rule baseline ("same symbol, opposite direction within 30s") across sealed seeds:

```bash
pytest tests/fraud/test_fraud_eval.py -v
```

**Expected Outcome**:
- Naive rule baseline achieves baseline PR-AUC (e.g. ~0.52).
- Machine-learning candidate-pruned pair detector achieves PR-AUC $\ge \text{Baseline} + 0.15$ (e.g. $\ge 0.67$).
- Hard-negative legitimate hedgers (`P-HARD-NEG-HEDGER-1`, `P-HARD-NEG-HEDGER-2`) have False Positive Rate $< 5.0\%$.

---

### Scenario 2: Batch Fraud Detection Pipeline
Execute the end-to-end partner fraud detection batch coordinator over synthetic affiliate cohorts:

```bash
python scripts/run_partner_fraud_pipeline.py --as-of 2026-10-07 --seed 42
```

**Expected Outcome**:
- Processes trading activity logs and partitions trades into sliding 30-second execution buckets.
- Identifies collusive pairs and computes `directional_type`, `timing_correlation_pct`, and `zero_sum_ratio`.
- Traverses the 3-layer sub-affiliate tree and aggregates exposure up to root Master Partners.
- Computes `ClientQualityIndex` and bonus abuse probabilities.
- Populates DuckDB tables: `partner_fraud_scores`, `partner_opposite_trading_pairs`, and `partner_fraud_cases`.
- Execution finishes in $< 30\text{s}$ for 5,000 synthetic partners.

---

### Scenario 3: OMCP Tool Surface Verification
Verify the four canonical OMCP tool handlers via unit and integration tests:

```bash
pytest tests/ontology/test_omcp_partner_fraud_tools.py -v
```

1. **`get_opposite_trading_pairs(partner_id="P-FRAUD-RING-01")`**: Returns identified opposite trading pairs with timing correlation metrics and zero-sum P&L extraction.
2. **`get_partner_referral_ring(partner_id="P-FRAUD-RING-01")`**: Returns the 3-layer network hierarchy graph mapped to the root Master Partner.
3. **`get_client_quality_profile(partner_id="P-FRAUD-RING-01")`**: Returns bonus harvesting velocity, fast-withdrawal counts, and client quality score.
4. **`get_partner_fraud_dossier(partner_id="P-FRAUD-RING-01")`**: Compiles the complete evidence dossier with sanitized narrative briefing.

All response payloads must validate strictly against contracts in [`contracts/`](contracts/).

---

### Scenario 4: Governed Action Intent & Four-Eyes Dual Approval
Verify non-autonomous mutation proposals and four-eyes enforcement:

```bash
python scripts/test_partner_fraud_intent.py --case-id CASE-FRAUD-OPPOSITE-01
```

**Expected Outcome**:
1. `PartnerFraudSpecialist` proposes `ClawbackCommission` for \$12,500 with evidence references.
2. Emits a Cloud KMS signed `ActionIntentToken` with `requires_dual_approval = True`.
3. First approval by Officer A updates status to `PENDING` (still awaiting second signature).
4. Direct execution attempt with 1 signature raises `FourEyesApprovalRequiredError`.
5. Second approval by Officer B updates status to `APPROVED`.
6. Execution proceeds against the simulated write-back sink and logs an immutable record in the `Decision_Ledger`.
