# Phase 1 Data Model: Layer 1 Ingestion Spine & Contract Gateway (F02)

**Feature**: `003-contracts-ingestion` | **Date**: 2026-10-04  
**Context**: Kinetic Enterprise Ontology — Layer 1 Logical Data Model  

This document defines the core data entities, schemas, relationship topologies, validation rules, and lifecycle state machines governing Layer 1.

---

## 1. Entity Relationship Diagram (ERD)

```text
┌─────────────────────────┐             ┌─────────────────────────┐
│   DataProductEvent      │──(passes)──▶│   DuckDB Hot State      │
│  (Incoming Event Msg)   │             │   (:memory:eios_hot_state)│
└────────────┬────────────┘             └────────────┬────────────┘
             │                                       │
         (breaches)                              (resolves)
             ▼                                       ▼
┌─────────────────────────┐             ┌─────────────────────────┐
│  ContractBreachRecord   │             │  CanonicalClientEntity  │
│  (DLQ / eios.l1.dlq.v1) │             │  (Single Client View)   │
└─────────────────────────┘             └────────────┬────────────┘
                                                     │
                                            ┌────────┴────────┐
                                            ▼                 ▼
                                 ┌──────────────────┐ ┌──────────────────┐
                                 │  LinkedIdentity  │ │ HubSuppressionTag│
                                 │ (MT5/Deriv/DP2P) │ │(is_shared_context│
                                 └──────────────────┘ └──────────────────┘
```

---

## 2. Core Entity Definitions

### 2.1 `DataProductEvent`
The universal wire envelope for all streaming events ingested through Pub/Sub or the HTTP push webhook.

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `event_id` | `UUID` | Required, Unique | Unique event identifier for end-to-end tracing and deduplication. |
| `product_name` | `String` | Required, Enum | Name of one of the 14 Layer 1 data products (e.g. `trading_activity`, `transactions_aml`). |
| `schema_version` | `String` | Required | Semantic contract version (e.g. `"1.0.0"`). |
| `event_timestamp` | `Timestamp(UTC)`| Required | Millisecond UTC timestamp when the business event occurred at source. |
| `tenant_id` | `String` | Required | Broker legal entity / regulatory boundary (e.g. `"DERIV_MFSA"`, `"DERIV_LFSA"`, `"DERIV_VFSC"`). |
| `payload` | `JSON Object` | Required | Typed event payload matching the data product's Pydantic model. |
| `source_metadata` | `JSON Object` | Optional | Emitting host, IP address, ingress protocol (`PUBSUB` vs `WEBHOOK`). |

---

### 2.2 `ContractBreachRecord`
The audit envelope generated when an incoming event fails Pydantic schema validation, null-rate bounds, or value domain constraints. Published to Dead-Letter Queue `eios.l1.dlq.v1`.

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `dlq_id` | `UUID` | Required, Unique | Unique identifier of the dead-letter record. |
| `event_id` | `String` | Required | Identifier of the originating event. |
| `product_name` | `String` | Required | Target data product that rejected the record. |
| `breach_timestamp`| `Timestamp(UTC)`| Required | Exact time when validation failure occurred. |
| `breach_type` | `String` | Enum | `SCHEMA_TYPE_ERROR`, `MISSING_REQUIRED_FIELD`, `NULL_RATE_EXCEEDED`, `VALUE_RANGE_VIOLATION`, `UNSANITIZED_PAYLOAD`. |
| `field_paths` | `List[String]` | Required | Dot-notation paths of failing fields (e.g. `["payload.amount", "payload.client_id"]`). |
| `error_messages` | `List[String]` | Required | Explanatory error diagnostics from the contract validator. |
| `raw_payload_bytes`| `String` (Base64)| Required | Raw payload preserved verbatim for forensic replay and zero-loss compliance. |
| `source_topic` | `String` | Required | Ingestion source topic or endpoint path. |

---

### 2.3 `CanonicalClientEntity`
The authoritative Single Client View (SCV) entity resolving a trader's identity across MetaTrader 5, Deriv Trader, Deriv P2P, and Payment Agent channels.

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `canonical_client_id` | `String` | Required, Unique | Stable platform identity prefix: `cl_canon_<hex:12>`. |
| `primary_pseudonym_token` | `String` | Required | Surrogate token representing the trader (`tok_client_<hex:16>`). |
| `kyc_status` | `String` | Enum | `APPROVED`, `PENDING`, `REJECTED`, `EDD_REQUIRED`. |
| `first_seen_ts` | `Timestamp(UTC)` | Required | Earliest recorded event timestamp across all linked accounts. |
| `last_seen_ts` | `Timestamp(UTC)` | Required | Latest activity timestamp. |
| `linked_identities` | `List[LinkedIdentity]` | Required | Subordinate accounts across source systems mapped to this client. |
| `associated_device_hashes` | `List[String]` | Optional | Cryptographic hashes of client WebGL/canvas hardware fingerprints. |
| `associated_ip_hashes` | `List[String]` | Optional | Salted hashes of client connection IP addresses. |
| `is_shared_context` | `Boolean` | Default: `False` | Flagged `True` if associated devices/IPs are hubs ($\ge 5$ distinct accounts). |
| `resolution_method` | `String` | Enum | `DETERMINISTIC_EXACT`, `PROBABILISTIC_FELLEXI_SUNTER`, `MANUAL_OVERRIDE`. |
| `confidence_score` | `Float` | Range: `[0.0, 1.0]` | Linkage confidence score. |

---

### 2.4 `LinkedIdentity`
Subordinate platform account attached to a `CanonicalClientEntity`.

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `link_id` | `UUID` | Required, Unique | Link record identifier. |
| `system_source` | `String` | Enum | `MT5`, `DERIV_TRADER`, `DP2P_ESCROW`, `PAYMENT_AGENT`. |
| `source_account_id` | `String` | Required | Native platform account ID (e.g. MT5 login number `10482910`). |
| `match_keys` | `List[String]` | Required | Keys participating in the match (e.g. `["tax_id_hash", "phone_hash"]`). |
| `match_weight` | `Float` | Required | Log-likelihood ratio match weight from Fellegi-Sunter model. |
| `linked_at` | `Timestamp(UTC)` | Required | Timestamp when linkage was asserted. |

---

### 2.5 `PseudonymTokenVaultEntry`
Cryptographic mapping table isolating sensitive PII from analytical queries. Stored in restricted key vault storage.

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `token_id` | `String` | Required, Unique | Surrogate token (e.g. `tok_client_3a8b...`). |
| `entity_type` | `String` | Enum | `CLIENT`, `PARTNER`, `DEVICE`, `PAYMENT_METHOD`. |
| `encrypted_plaintext` | `String` (Base64) | Required | Plaintext PII encrypted using AES-256-GCM. |
| `hmac_hash` | `String` | Required | Blind index hash used for deterministic token lookup. |
| `key_version` | `String` | Required | Secret key version used for rotation tracking (e.g. `"v1"`). |
| `created_at` | `Timestamp(UTC)` | Required | Ingestion creation timestamp. |

---

### 2.6 `DataQualityReport`
Real-time operational health snapshot for an individual data product.

| Field Name | Type | Constraint | Description |
|---|---|---|---|
| `product_name` | `String` | Required | One of the 14 Layer 1 data products. |
| `status` | `String` | Enum | `HEALTHY`, `DEGRADED`, `CRITICAL`. |
| `freshness_lag_seconds` | `Float` | Required | Current lag: $T_{\text{now}} - \max(T_{\text{event}})$. |
| `freshness_sla_seconds` | `Float` | Required | SLA maximum allowable lag threshold (e.g. 30.0s). |
| `breach_count_1h` | `Integer` | Required | Total contract breach events diverted to DLQ in the past 1 hour. |
| `breach_rate_1h` | `Float` | Required | Percentage of incoming records breaching contract ($\text{breaches} / \text{total}$). |
| `null_rate_map` | `Map[String, Float]` | Required | Per-column observed null rate vs configured threshold. |
| `last_rehydration_ts` | `Timestamp(UTC)` | Required | Timestamp of last Parquet warm-start execution. |
| `rehydration_duration_ms` | `Float` | Required | Milliseconds required to warm-start table into DuckDB. |

---

## 3. State Machines & Lifecycle Transitions

### 3.1 Data Product Health State Machine

```text
                     ┌──────────────────┐
                     │     HEALTHY      │
                     └────────┬─────────┘
                              │
          (Freshness Lag > SLA OR Breach Rate > 0.05%)
                              │
                              ▼
                     ┌──────────────────┐
                     │     DEGRADED     │◀───┐
                     └────────┬─────────┘    │
                              │              │
           (Breach Rate > 5.0% OR System Err)│ (Remediation / Replay)
                              │              │
                              ▼              │
                     ┌──────────────────┐    │
                     │     CRITICAL     │────┘
                     └──────────────────┘
```

1. **`HEALTHY`**: Normal state. 100% contract compliance, freshness lag $\le \text{SLA}$.
2. **`DEGRADED`**: Warning state. Triggered when contract breach rate exceeds $0.05\%$ in rolling 1-hour window OR freshness lag exceeds product SLA. An operational alert is emitted and downstream dashboards display an amber Freshness/Integrity banner. Hot state continues serving valid historical records.
3. **`CRITICAL`**: Emergency state. Breach rate exceeds $5.0\%$ or hot-state rehydration fails completely. Ingestion circuit breaker triggers throttling and pages on-call.

---

### 3.2 Single Client View Resolution Lifecycle

```text
Incoming Fragmented Record (MT5 / Deriv / DP2P)
                 │
                 ▼
     [Deterministic Exact Key Scan]
     (Tax ID Hash, Phone Hash, Email Hash)
        │                              │
        │ (Exact Match Found)          │ (No Exact Match)
        ▼                              ▼
 [Merge into Canonical SCV]    [Probabilistic Match Scan]
 (Confidence = 1.0)            (Name Jaro-Winkler, Device Hash)
                                       │
                          ┌────────────┴────────────┐
                          │ Match Weight >= Threshold│ Match Weight < Threshold
                          ▼                         ▼
               [Check Hub Suppression]     [Create New Canonical SCV]
               (Device/IP Degree >= 5?)
                 │                 │
           (Yes) │                 │ (No)
                 ▼                 ▼
          [Do NOT Merge]     [Merge into Existing SCV]
          Tag is_shared_context
```
