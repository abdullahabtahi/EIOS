# Quickstart: F01 Synthetic Enterprise Data Foundry — Validation Guide

**Feature**: `002-synthetic-foundry` | **Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

This document provides runnable validation procedures to verify all functional requirements and success criteria of the Layer 0 Synthetic Enterprise Data Foundry (F01).

---

## Prerequisites

1. Python 3.11+ environment with `eios` package and testing tools installed (`pytest`, `pyarrow`, `pydantic>=2.0`, `faker`).
2. Local mock directory structure initialized (`data/raw/`, `fixtures/eval_truth/`).
3. Clean Git checkout (or consistent content hash).

---

## Validation Scenarios

### 1. Byte-for-Byte Determinism Test (SC-001, FR-001, FR-002)

1. Execute the foundry runner with manifest seed `42`:
   ```bash
   python -m eios.foundry.cli generate --tier dev --seed 42 --output-dir data/run_a/
   ```
2. Capture the SHA-256 Merkle root of all emitted Parquet partitions:
   ```bash
   python -m eios.foundry.cli verify-hash --dataset-dir data/run_a/
   ```
3. Execute the foundry runner a second time with the exact same manifest:
   ```bash
   python -m eios.foundry.cli generate --tier dev --seed 42 --output-dir data/run_b/
   ```
4. Verify that:
   - Every individual `.parquet` file in `data/run_a/` has an identical SHA-256 hash to its counterpart in `data/run_b/`.
   - The master `dataset_hash` in `manifest.yaml` matches identically across both runs `[TARGET]`.

---

### 2. L1 Contract Compliance & Deliberate Breach Rejection (SC-002, SC-007, FR-010)

1. Run the contract validation audit across all generated datasets:
   ```bash
   pytest tests/contract/test_foundry_l1_contracts.py
   ```
2. Verify 100% of generated records pass Pydantic models for `client_360`, `transactions_aml`, `partner_360`, `financial_pnl`, etc. without transformation errors (`SC-002`).
3. Inject a deliberate contract mutation into a test fixture (e.g. invalid string for transaction amount):
   ```bash
   python -m eios.foundry.cli test-breach-injection
   ```
4. Confirm the generator crashes immediately with exit code `42 (ContractValidationError)` and logs the offending record, verifying `SC-007`.

---

### 3. Synthetic PII Scan (SC-003, FR-009)

1. Execute the automated PII scanner across all emitted string fields in `client_360` and `partner_360`:
   ```bash
   python -m eios.tools.pii_scanner scan --input-dir data/run_a/
   ```
2. Confirm:
   - 0 real-world customer email domains or identities detected.
   - 100% of names and addresses trace to seeded `Faker` generator dictionaries.
   - No real financial institution names or real broker names (e.g. Exness, XM) appear.

---

### 4. Ground-Truth Bucket Isolation & IAM Deny Simulation (SC-004, FR-008)

1. Simulate an L3 Reasoning Mesh agent attempting to read from `eval-truth/`:
   ```bash
   python -m eios.foundry.cli test-iam-isolation --role reasoning-mesh
   ```
2. Confirm the access attempt is actively denied (`PermissionError: Access to eval-truth denied for role reasoning-mesh`).
3. Confirm the Evaluation Harness identity (`role: eval-harness`) successfully reads ground truth (`SC-004`).

---

### 5. Brief Typology & Graph Ring Verification (SC-005, FR-019, FR-020, FR-027, FR-028, FR-031, FR-048)

1. Inspect the ground truth outputs in `eval-truth/`:
   ```bash
   python -m eios.foundry.cli verify-ground-truth --dir fixtures/eval_truth/
   ```
2. Confirm:
   - `syndicate_47`: Contains exactly 47 unique `client_id` entries linked by shared devices and IPs.
   - `round_trip_laundering`: Contains transactions matching $\$500.00$ deposit $\rightarrow$ 10 min hold $\rightarrow$ $\$0.01$ trade $\rightarrow$ withdrawal request.
   - `partner_ring_7_23_184`: Contains 7 master partners, 23 sub-affiliates, and 184 clients across 3 layers.
   - `mirror_trading`: Contains 23 pairs of client accounts with trade correlation $\ge 0.89$ and net P&L $\approx \$0.00$.
   - `traffic_fraud`: Lists exactly 12 partner IDs with anomalous bot conversion rates.
   - `placebo_edge`: Explicitly identifies the placebo edge in the causal DAG with true structural effect $= 0.0$.

---

### 6. Hub-Suppression Hard Negative Stress Test (SC-006, FR-023)

1. Run the hub query against the generated network graph:
   ```bash
   python -m eios.foundry.cli verify-hub-suppression --data-dir data/run_a/
   ```
2. Confirm:
   - At least 1 IP address is shared by $\ge 500$ distinct client accounts (`SC-006`).
   - The ground truth tags this IP as `is_hub_node: true` and `benign: true`.
   - None of the 500 accounts are members of the 47-account syndicate ring.

---

### 7. Driver Attribution Sums to 100.0% (SC-008, FR-049)

1. Verify the ground-truth driver decomposition file:
   ```bash
   python -m eios.foundry.cli verify-driver-split --file fixtures/eval_truth/forecast_driver_split.json
   ```
2. Confirm the sum of all percentage drivers equals exactly $100.0\%$ (e.g. $40.0\% + 35.0\% + 25.0\% = 100.0\%$).

---

### 8. Sealed Holdout Tier & Novel Typology Verification (SC-009, FR-004, FR-005, FR-006)

1. Attempt to generate `sealed` data locally without the CI environment flag:
   ```bash
   python -m eios.foundry.cli generate --tier sealed --seed 9001
   ```
   *Expected Outcome*: Fails with `PermissionError: Sealed datasets can only be generated in CI release-candidate runs` (`FR-004`).
2. Run with `CI_RELEASE_CANDIDATE=true`:
   ```bash
   CI_RELEASE_CANDIDATE=true python -m eios.foundry.cli generate --tier sealed --seed 9001 --output-dir data/sealed_run/
   ```
3. Inspect ground truth in `data/sealed_run/eval-truth/`:
   - Confirm distribution shifts are present (transaction volume modified by $\pm 15\%$).
   - Confirm at least two ($\ge 2$) novel typologies (*Typology Alpha* and *Typology Beta*) are present in `sealed` and completely absent from `dev` (`SC-009`).

---

## Coverage Map

| Success Criterion | Validating Scenario | Target Metric / Rule |
|---|---|---|
| **SC-001** | Scenario 1 | 100% identical SHA-256 Merkle root across repeated runs `[TARGET]` |
| **SC-002** | Scenario 2 | 100% records pass L1 Pydantic contracts `[TARGET]` |
| **SC-003** | Scenario 3 | 100% synthetic PII; 0 real broker/entity names `[TARGET]` |
| **SC-004** | Scenario 4 | 0 read permissions for reasoning mesh on eval bucket `[TARGET]` |
| **SC-005** | Scenario 5 | 47-account ring, 7/23/184 ring, 12 bot partners in ground truth |
| **SC-006** | Scenario 6 | $\ge 1$ IP shared by $\ge 500$ unlinked accounts |
| **SC-007** | Scenario 2 | Generator terminates loudly on contract mutation |
| **SC-008** | Scenario 7 | Driver attribution percentages sum to 100.0% exactly |
| **SC-009** | Scenario 8 | $\ge 2$ novel typologies present in sealed holdout |
