# Quickstart & Validation Guide: Layer 2 Kinetic Ontology & Semantic Metric Layer (F03)

**Branch**: `004-ontology-metrics` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

This guide documents runnable validation scenarios that prove the Layer 2 Kinetic Ontology and Metric Layer functions end-to-end against production quality bars.

---

## 1. Prerequisites & Setup

Ensure the Python environment is synchronized with the latest dependencies:

```bash
cd FEIOS
uv sync
```

Verify that all baseline dependencies (`duckdb`, `networkx`, `fastapi`, `pydantic`, `cryptography`) are active:

```bash
uv run python -c "import duckdb, networkx, pydantic, cryptography; print('Environment Ready')"
```

---

## 2. Validation Scenarios

### Scenario 1: Governed Metric Query Latency ($\le 10\text{ms}$)
Validates that `get_metric` queries execute deterministically against in-memory DuckDB hot state without cold-cache penalty.

```bash
# Execute metric registry benchmark against 100,000 synthetic transactions
uv run python -m eios.ontology.metrics.benchmark
```
*Expected Outcome*:
- P95 query execution time $\le 10.0\text{ms}$ (`SC-001`).
- Returned payload matches `contracts/metric-registry-catalog.md` schema with exact numeric precision, `unit: "USD"`, and `definition_version: "1.0.0"`.

### Scenario 2: In-Memory Property Graph Rehydration & Hub Suppression
Validates that 50,000 nodes and 150,000 edges rehydrate in $< 1.5\text{s}$, and nodes with degree $\ge 5$ (e.g. carrier NATs or family tablets) are flagged with `is_shared_context=True`.

```bash
# Run graph rehydration and hub suppression validation
uv run pytest tests/ontology/test_property_graph.py -k "test_hub_suppression"
```
*Expected Outcome*:
- Cold-boot graph initialization completes in $< 1.5\text{s}$ (`SC-004`).
- Multi-hop traversal with `suppress_hubs=True` prunes carrier NAT supernodes, achieving $\le 0.1\%$ false merges (`SC-006`).

### Scenario 3: Metric Auditor Gate Egress Firewall (Red-Line RL-1)
Validates that the Metric Auditor Gate blocks 100% of responses containing unanchored, hallucinated numbers.

```bash
# Run adversarial numerical hallucination test suite
uv run pytest tests/ontology/test_auditor_gate.py
```
*Expected Outcome*:
- Responses citing tool numbers (`$142,500 across 38 clients`) pass with `audit_passed=True`.
- Responses with unanchored numbers (`churn increased by 34.2%`) are blocked with `audit_passed=False` and `untraceable_numbers: ["34.2%"]` (`SC-002`).

### Scenario 4: Governed Action Intent Signing & Four-Eyes Enforcement
Validates that `propose_action` generates a valid Cloud KMS ECDSA P-256 signature, prevents replay of nonces, and enforces four-eyes approval on High severity actions.

```bash
# Run action intent lifecycle tests
uv run pytest tests/ontology/test_action_intents.py
```
*Expected Outcome*:
- Token signature verifies using ECDSA P-256 public key.
- Attempting to execute an unapproved or expired token ($> 15\text{min}$) fails immediately.
- High severity actions require 2 distinct approvers before emitting to the write-back sink (`SC-003`).

### Scenario 5: OMCP Security Markings & PII Vault Isolation
Validates that OMCP tool endpoints filter sensitive data based on caller role and ensure PII is strictly returned as pseudonymized tokens.

```bash
# Run security marking and OMCP tool contract tests
uv run pytest tests/ontology/test_omcp_tools.py
```
*Expected Outcome*:
- Plaintext PII is never returned; all names/tax IDs are `tok_client_<hex16>`.
- `SENSITIVE_COMPLIANCE` cases return `InsufficientMarkingError` when queried by commercial roles (`SC-007`).

---

## 3. Full Test Suite & Coverage Gate

Run the complete Layer 2 test suite and verify the $\ge 80\%$ test coverage gate:

```bash
uv run pytest tests/ontology/ --cov=eios.ontology --cov-report=term-missing --cov-fail-under=80
```
*Expected Outcome*: All tests pass with $\ge 80\%$ line and branch coverage (`SC-008`).
