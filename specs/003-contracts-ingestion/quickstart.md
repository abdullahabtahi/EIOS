# Phase 1 Quickstart Guide: Layer 1 Ingestion Spine & Contract Gateway (F02)

**Feature**: `003-contracts-ingestion` | **Date**: 2026-10-04  
**Context**: QuantumBlack / Palantir FDE Validation Scenarios  

This document provides runnable validation steps to verify the Layer 1 Ingestion Spine, Contract Validation Gate, DuckDB Hot-State Engine, and Entity Resolution service end-to-end.

---

## Prerequisites

1. Active Python 3.11+ virtual environment managed by `uv`:
   ```bash
   cd FEIOS
   uv sync
   ```
2. Synthetic Layer 0 Parquet lakehouse files present in `data/raw/` (or generated via `uv run python -m eios.foundry.cli generate --profile dev`).

---

## Validation Scenario 1: Cold-Boot Warm-Start Rehydration & Health Probes

Prove that the DuckDB in-memory hot-state engine (`:memory:eios_hot_state`) rehydrates the 14 data product baseline tables from Parquet lakehouse partitions in $< 3.0\text{s}$ (ADR-012), and that container health probes reflect state.

```bash
# Execute the warm-start benchmark test
uv run pytest tests/contracts/test_warm_start.py -v -k "test_cold_boot_rehydration_under_3s"
```

**Expected Outcome**:
- Startup log records rehydration duration: `Warm-start rehydration completed in 1.42s (< 3.0s threshold)`.
- Readiness probe returns HTTP 200:
  ```bash
  curl -i http://localhost:8080/readyz
  # HTTP/1.1 200 OK
  # {"status": "READY", "warm_start_duration_ms": 1420.5, "loaded_products": 14}
  ```

---

## Validation Scenario 2: Webhook Ingestion & Pydantic Contract Validation

Post a valid trade execution event to the synchronous ingestion endpoint and verify sub-50ms acknowledgement and queryable presence in DuckDB hot state.

```bash
# Send valid trade payload
curl -X POST http://localhost:8080/v1/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "product_name": "trading_activity",
    "schema_version": "1.0.0",
    "event_timestamp": "2026-10-04T12:00:00Z",
    "tenant_id": "DERIV_MFSA",
    "payload": {
      "trade_id": "TRD_98241029",
      "client_id": "CR84920",
      "symbol": "BOOM_1000",
      "side": "BUY",
      "volume": 2.5,
      "open_price": 1042.50,
      "open_ts": "2026-10-04T12:00:00Z"
    }
  }'
```

**Expected Outcome**:
- Response: `HTTP/202 Accepted` with receipt ID in $< 50\text{ms}$.
- Event queryable in DuckDB hot state:
  ```bash
  uv run python -c "
  from eios.ingestion.hot_state import get_hot_state
  res = get_hot_state().query(\"SELECT trade_id, symbol, volume FROM trading_activity WHERE trade_id = 'TRD_98241029'\")
  print(res.fetchall())
  "
  # [('TRD_98241029', 'BOOM_1000', 2.5)]
  ```

---

## Validation Scenario 3: Breach Injection & DLQ Circuit Breaker (Principle IV)

Inject a malformed payload (negative deposit amount and null required fields) and prove that:
1. Zero records are silently dropped.
2. The payload is intercepted and diverted to `eios.l1.dlq.v1`.
3. The parent product status automatically toggles to `DEGRADED`.

```bash
# Send invalid transaction event (negative amount, missing client_id)
curl -X POST http://localhost:8080/v1/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "product_name": "transactions_aml",
    "schema_version": "1.0.0",
    "event_timestamp": "2026-10-04T12:05:00Z",
    "tenant_id": "DERIV_LFSA",
    "payload": {
      "txn_id": "TXN_ERR_001",
      "amount": -500.0,
      "currency": "USD"
    }
  }'
```

**Expected Outcome**:
- Record diverted to DLQ envelope and logged as structured `CONTRACT_BREACH`.
- Verify Data Quality status endpoint reflects degradation:
  ```bash
  curl -s http://localhost:8080/v1/dq/status | jq '.products.transactions_aml'
  ```
  Output:
  ```json
  {
    "status": "DEGRADED",
    "freshness_lag_seconds": 12.4,
    "freshness_sla_seconds": 30.0,
    "breach_count_1h": 1,
    "breach_rate_1h": 0.08
  }
  ```

---

## Validation Scenario 4: Single Client View Entity Resolution & Hub Suppression (ADR-008)

Execute cross-platform entity resolution linking MT5, Deriv Trader, and DP2P identities while proving that shared family devices ($\ge 5$ accounts) are suppressed from false merging.

```bash
uv run pytest tests/contracts/test_entity_resolution.py -v
```

**Expected Test Verifications**:
- MT5 login `#109281` and Deriv Trader client `#CR84920` sharing Tax ID hash resolve to the identical `canonical_client_id` (Confidence = 1.0).
- Expatriate family tablet sharing hardware hash across 5 distinct tax IDs is tagged with `is_shared_context=True`; distinct family member accounts **remain separate entities** (False merge rate $\le 0.1\%$).

---

## Validation Scenario 5: PII Pseudonymization Token Vault (Marking P)

Verify that raw client PII (names, plain emails, phone numbers) is tokenized into deterministic surrogate tokens and that zero plaintext PII leaks into DuckDB hot state.

```bash
uv run pytest tests/contracts/test_pii_vault.py -v
```

**Expected Test Verifications**:
- Plain email `trader_john@example.com` tokenizes to `tok_client_7a9f...`.
- In-memory table scan for `trader_john@example.com` returns 0 rows.
- Re-tokenization of the same email in a separate data product produces identical token `tok_client_7a9f...` (referential integrity preserved).

---

## Validation Scenario 6: Full Test Suite & Coverage Gate Execution

Execute the entire Layer 1 test suite and assert that line and branch coverage exceeds the $80\%$ minimum gate:

```bash
uv run pytest tests/contracts/ --cov=src/eios/ingestion --cov-fail-under=80
```
