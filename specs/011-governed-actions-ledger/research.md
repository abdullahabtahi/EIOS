# Research & Architectural Trade-offs: Governed Actions & Decision Ledger (F10 / Slice S5)

**Feature**: `011-governed-actions-ledger`  
**Date**: 2026-10-08  
**Status**: Completed  
**Authoritative References**: `initial_plan.md` §6.1, §6.2, §5.1, `docs/brief/monitoring.md`, `docs/brief/fraud.md`, `.specify/memory/constitution.md` (Principles I, II, IV, V, VI, VII, VIII)

---

## 1. Upstream Transactional Sequencer & Hash Chaining (ADR-017)

### Context & Challenge
BigQuery and cloud-native distributed data warehouses utilize high-throughput streaming ingestion (`storage_write_api` / streaming inserts). These distributed write paths do not guarantee total deterministic ordering across concurrent micro-batches, nor can they intrinsically detect missing rows or out-of-order writes without external sequencing. In a financial intelligence platform, if an attacker or system failure drops or alters an audit record, the analytical store cannot detect the gap.

### Technical Decision
Implement an upstream in-memory/transactional **`LedgerSequencer`** that sits between proposing agents/approvers and the persistence layer.
1. The sequencer maintains a strictly monotonic integer sequence counter: $\text{ledger\_seq} = 1, 2, 3, \ldots, N$.
2. For each transaction $i$, it computes a cryptographic hash chain:
   $$H_i = \text{SHA-256}\left(H_{i-1} \parallel \text{ledger\_seq}_i \parallel \text{payload\_digest}_i\right)$$
   where $H_0$ is a pre-registered genesis hash anchor:
   $$H_0 = \text{SHA-256}(\text{"EIOS\_GENESIS\_ANCHOR\_V1\_20261008"})$$
3. The sequencer enforces atomicity via thread-safe transactional locks, ensuring that every proposal, approval, execution, and compensation event is serialized and hashed before being committed to DuckDB hot state (`atomic_sequence_ledger`) and downstream analytical pipelines.

### Rationale
- **Total Monotonic Ordering**: Guarantees zero sequence gaps ($S_i = S_{i-1} + 1$). Any missing or out-of-order write is detected immediately.
- **Linear Hash Chain vs. Merkle Tree DAG**: For an append-only sequential transaction stream, linear hash chaining requires $O(1)$ append time and $O(1)$ memory overhead. Merkle trees introduce tree-rebalancing and branch-proof overhead that is valuable for sparse distributed proofs (e.g. Git, BitTorrent) but adds unnecessary latency to high-throughput sequential audit logging.
- **Microsecond Latency**: In-memory sequencing and SHA-256 hashing executes in $< 15\,\mu\text{s}$ per transaction, well within the $< 100\,\text{ms}$ execution latency budget.

### Alternatives Considered
- **BigQuery `ROW_NUMBER() OVER (ORDER BY timestamp)`**: Rejected because distributed clocks suffer from clock skew (up to tens of milliseconds in multi-region environments), causing race conditions and non-deterministic ordering for concurrent transactions. Furthermore, window functions cannot detect if an entire row was deleted.
- **Distributed Raft/Paxos Log**: Overkill for the single-region operational coordinator layer in EIOS, adding heavyweight networking dependencies and consensus latency ($10\text{–}50\,\text{ms}$) where an upstream serialized coordinator is sufficient.
- **Database Auto-Increment Columns**: Subject to transaction rollbacks that create unrecorded sequence gaps, violating compliance requirements where every integer sequence number must be accounted for.

---

## 2. Governed Two-Phase Commit State Machine & Four-Eyes Authorization

### Context & Challenge
AI agents cannot be permitted to autonomously execute operational mutations such as freezing client trading accounts, seizing partner commission balances, or withholding client withdrawal payouts. Such actions carry irreversible legal, financial, and reputational ramifications. Regulatory frameworks (FATF, FinCEN 31 CFR 1010, FCA) and Constitution Principle II explicitly mandate human oversight.

### Technical Decision
Implement a governed **Two-Phase Commit (2PC) State Machine**:
- **Phase 1 (Proposal)**: Agent proposes action via `propose_action()`. The system validates required parameters against `CANONICAL_ACTION_SPECS`, generates a unique `intent_id`, generates a 128-bit single-use cryptographic `nonce`, issues a Cloud KMS asymmetric ECDSA P-256 signature, stamps a 15-minute expiration timestamp, and records the token in status `PENDING`.
- **Phase 2 (Approval)**:
  - **High-Severity Actions** (`HoldWithdrawal`, `FreezeAccount`, `ClawbackCommission`, `SuspendPartner`): Mandates **Four-Eyes Authorization**—strictly two distinct authenticated human approvers (`approver_id_1 != approver_id_2`). The first approval leaves the token in `PENDING` with tag `DUAL_APPROVAL_MANDATORY`; the second approval transitions the token to `APPROVED`.
  - **Medium/Low-Severity Actions** (`LaunchRetentionPlaybook`, `AdjustPartnerTier`): If financial impact $\le \$2,500.00$ (policy threshold), a single authorized manager approval transitions the token directly to `APPROVED` under the fast-path policy.
- **Phase 3 (Commit)**: Execution via `execute_action()` commits the mutation strictly against the `SimulatedWriteBackSink`. The intent transitions to `EXECUTED` (or `ABORTED` if an unrecoverable fault occurs).

### Rationale
- **Non-Negotiable Principle II Compliance**: Eliminates any possibility of unapproved or autonomous agent write-back.
- **Separation of Duties**: Four-eyes authorization ensures collusion-resistant governance for high-risk actions.
- **Operational Ergonomics**: Fast-path threshold prevents workflow bottlenecks on low-risk customer retention campaigns while maintaining a complete audit trail.

### Alternatives Considered
- **Single Approver for All Actions**: Rejected due to regulatory non-compliance for high-severity capital actions ($> \$10,000$ or permanent account freezes).
- **Post-Execution Rollback**: Rejected because notifying payment processors or freezing client accounts cannot be silently "rolled back" without public customer impact and regulatory exposure.

---

## 3. Cryptographic Signature Scheme: Cloud KMS ECDSA P-256 vs. HMAC-SHA256

### Context & Challenge
Action intent tokens must be cryptographically non-repudiable and tamper-evident across distributed services, downstream workers, and regulatory audits.

### Technical Decision
Use **ECDSA with NIST P-256 (SECP256R1) and SHA-256** signatures, formatted as ASN.1 DER base64 strings, operating over canonical JSON byte representations (RFC 8785) of the intent payload.
- In production, signed via Google Cloud KMS Asymmetric Keys (`EC_SIGN_P256_SHA256`).
- In local testing, executed via `KMSActionSigner` using `cryptography.hazmat.primitives.asymmetric.ec` with an in-memory SECP256R1 keypair.

### Rationale
- **Public Verifiability**: With asymmetric cryptography, any downstream service, auditor, or client can verify the token's validity using only the public key. The private signing key never leaves Cloud KMS or the secure signing enclave.
- **Industry Standard**: ECDSA P-256 is the standard asymmetric curve mandated by FIPS 186-4, Google Cloud KMS, and financial security baselines.
- **Deterministic Canonical Serialization**: Sorting dictionary keys and eliminating whitespace (RFC 8785) prevents byte-level serialization variations from invalidating valid signatures.

### Alternatives Considered
- **HMAC-SHA256 (Symmetric)**: While computationally cheaper, HMAC requires the shared secret to be distributed to every verifying service, creating high-risk key exposure vectors.
- **RSA-4096**: Offers equivalent security but produces large signatures (512 bytes vs. ~71 bytes DER) and significantly higher CPU signing overhead.
- **Ed25519**: Excellent performance, but not universally supported across legacy enterprise HSMs and older Google Cloud KMS configurations compared to NIST P-256.

---

## 4. WORM Chain-Head Checkpoint Anchoring (GCS Object Retention Lock)

### Context & Challenge
Even with a cryptographic hash chain, if an adversary gains root access to the database hosting the ledger table, they could theoretically tamper with row $K$, recompute all downstream hashes $H_K, H_{K+1}, \ldots, H_N$, and rewrite the database table unnoticed by local checks.

### Technical Decision
Implement **Periodic WORM (Write-Once-Read-Many) Chain-Head Anchoring**:
1. At periodic intervals (e.g. every 100 transactions or hourly), the system extracts the latest `ledger_seq` and `current_hash`.
2. A checkpoint payload is formed:
   ```json
   {
     "checkpoint_seq": 1,
     "chain_head_seq": 100,
     "chain_head_hash": "4a7f...",
     "locked_at": "2026-10-08T08:00:00Z",
     "retention_until": "2033-10-08T08:00:00Z",
     "compliance_mode": true
   }
   ```
3. The checkpoint is written to an immutable WORM storage repository simulating **Google Cloud Storage Object Retention Lock in Compliance Mode** (`bucket.lock_retention_policy()`).
4. In Compliance Mode, the retention policy cannot be shortened or removed by anyone—including the Google Cloud Project Owner or storage administrators—until the retention period expires.
5. In local/test mode, simulated via `WORMAnchorService` maintaining an append-only, overwrite-protected ledger table (`worm_anchor_checkpoints`).

### Rationale
- **Guaranteed Immutability**: Provides mathematical and operational proof against insider threats and database-level rewriting attacks.
- **Regulatory Alignment**: Satisfies SEC Rule 17a-4, FINRA Rule 4511, and CFTC 1.31 compliance mandates for electronic records storage.

### Alternatives Considered
- **Public Blockchain Anchoring (Ethereum / Bitcoin)**: Rejected due to variable confirmation times (12 seconds to 10 minutes), volatile transaction fees (gas costs), and introducing external Web3 dependencies into an enterprise banking stack.
- **Standard GCS Buckets Without Retention Lock**: Rejected because any compromised IAM Service Account with `storage.admin` could overwrite or delete objects.

---

## 5. Continuous Cryptographic Audit Walker

### Context & Challenge
Ledger integrity must be proactively verified in real time, not merely evaluated after an audit subpoena or security breach occurs.

### Technical Decision
Implement an automated **`ContinuousAuditWalker`**:
1. Traverses the entire ledger sequentially from `ledger_seq = 1` to head.
2. At sequence 1, verifies that `prev_hash` equals the known genesis anchor.
3. At each sequence $i$, verifies:
   - Sequence continuity: $\text{ledger\_seq}_i == \text{ledger\_seq}_{i-1} + 1$.
   - Hash linkage: $\text{prev\_hash}_i == \text{current\_hash}_{i-1}$.
   - Payload re-hash: $\text{current\_hash}_i == \text{SHA-256}(\text{prev\_hash}_i \parallel \text{ledger\_seq}_i \parallel \text{payload\_digest}_i)$.
4. Cross-checks against all recorded WORM checkpoints: verifies that for checkpoint $(S, H)$, the ledger entry at sequence $S$ matches $H$ exactly.
5. Emits an **`AuditVerificationReport`**:
   - `total_entries`: Integer count of checked records.
   - `is_valid`: Boolean (True if 100% intact).
   - `integrity_score`: Float ($1.0$ if intact, $< 1.0$ if tampered).
   - `tampered_sequence_id`: Exact integer sequence number where the first mismatch occurred (None if valid).
   - `failure_reason`: Descriptive explanation of corruption (e.g. `PAYLOAD_TAMPERING_DETECTED`, `SEQUENCE_GAP_DETECTED`, `WORM_ANCHOR_MISMATCH`).

### Rationale
- **100% Tamper Detection Precision**: Mathematically pinpoints single-byte alterations or deleted rows instantly.
- **Zero-False-Positive Auditing**: Deterministic cryptographic verification eliminates subjective heuristic false alarms.

### Alternatives Considered
- **Database Trigger Checks**: Database triggers only fire on active write operations and do not detect offline storage file manipulation or direct disk edits.
- **Periodic Snapshot Diffing**: Fails to detect intermediate additions and deletions within the snapshot window.

---

## 6. Simulated Core Write-Back Sink with Chaos Fault Injection

### Context & Challenge
Real-time enterprise intelligence agents must interact with core banking ledgers, card clearinghouses, CRM platforms, and partner commission engines. However, live write-back in staging or portfolio evaluation environments is either dangerous or prohibited.

### Technical Decision
Implement a dedicated **`SimulatedWriteBackSink`**:
1. Serves as the sole authorized execution sink for `APPROVED` action intents.
2. Enforces idempotency via client-provided or token-derived `idempotency_key`, guaranteeing that retried execution requests return the existing receipt without double-executing mutations.
3. Records all execution events into `simulated_writeback_ledger` in hot state.
4. Supports configurable **Chaos Fault Injection Modes**:
   - `FaultMode.NONE`: Normal deterministic execution ($< 100\,\text{ms}$, emits `ExecutionReceipt`).
   - `FaultMode.NETWORK_TIMEOUT`: Simulates core banking gateway timeout; triggers intent transition to `ABORTED` and logs compensation intent.
   - `FaultMode.LEDGER_CONFLICT`: Simulates concurrent account lock collision; returns retryable error and records failure receipt.
   - `FaultMode.CORE_REJECTION`: Simulates downstream policy veto (e.g. account already frozen); records terminal rejection receipt.

### Rationale
- **Isolated Realism**: Provides realistic external reference IDs, settlement timestamps, and operational side-effects without risk to live banking systems.
- **Chaos Resilience Testing**: Proves that the two-phase commit protocol handles distributed failures cleanly pursuant to Constitution Principle VIII.

### Alternatives Considered
- **Mock HTTP Server (WireMock / Prism)**: Extra subprocess overhead and network socket instability in unit tests.
- **Stub Function / In-Memory Dict**: Lacks idempotency deduplication, simulated settlement latencies, and structured receipt verification.

---

## 7. Multi-Horizon Decision Outcomes Ledger & AIPW Counterfactual Tracking

### Context & Challenge
When evaluating automated intervention policies (e.g. VIP retention bonuses or account freeze policies), human compliance officers and account managers exhibit **"confounding by indication"**: they selectively approve or reject interventions based on private or high-dimensional signals not captured by simple rules. Naive observational comparisons of treated vs. untreated accounts produce severely biased causal effect estimates.

### Technical Decision
1. **At Proposal Time**: Every `ActionIntentToken` captures:
   - Proposing agent propensity score: $e(X) = P(W = 1 \mid X) \in (0, 1)$.
   - Full causal context vector: $X \in \mathbb{R}^d$ (trading turnover, recency, risk score, partner tier, churn probability).
2. **At Approval Time**:
   - Human sign-offs record `manager_override_flag = TRUE/FALSE` and documented qualitative justification if the manager diverged from the agent's recommended action or budget.
3. **In `decision_outcomes_ledger`**:
   - Records the tuple $(Y, W, e(X), X, \text{override})$ across multiple forward observation horizons (30-day, 60-day, and 90-day).
   - Persists observed actuals: `observed_retained_revenue_30d`, `actual_churn_60d`, `clawback_recovered_usd_90d`.
4. **Offline Causal Recalibration**: Downstream causal ML models use **Doubly Robust Augmented Inverse Probability Weighting (AIPW)**:
   $$\hat{\tau}_{\text{AIPW}} = \frac{1}{N} \sum_{i=1}^N \left[ \left(\hat{\mu}_1(X_i) - \hat{\mu}_0(X_i)\right) + \frac{W_i (Y_i - \hat{\mu}_1(X_i))}{\hat{e}(X_i)} - \frac{(1 - W_i)(Y_i - \hat{\mu}_0(X_i))}{1 - \hat{e}(X_i)} \right]$$
   where $\hat{\mu}_w(X)$ is the outcome regression model and $\hat{e}(X)$ is the treatment propensity model.

### Rationale
- **Double Robustness**: The estimated Average Treatment Effect $\hat{\tau}_{\text{AIPW}}$ is statistically consistent and unbiased if *either* the propensity score model $\hat{e}(X)$ *or* the conditional outcome model $\hat{\mu}(X)$ is correctly specified.
- **Manager Override Debbiasing**: By explicitly logging manager overrides as a covariate, the model isolates human selection bias from agent policy impact.

### Alternatives Considered
- **Unweighted Observational Regression (OLS / Ordinary Regression)**: Fails catastrophically due to selection bias (treated accounts look worse because only severe accounts were treated).
- **Randomized Controlled Trials (RCT) on Fraud Actions**: Ethically and legally impermissible (cannot randomly allow money laundering to observe counterfactual fraud losses).

---

## 8. Summary of Component Integration Architecture

| Component | Class / Service | Primary Responsibility | Target Latency / SLA |
|---|---|---|---|
| **Upstream Sequencer** | `LedgerSequencer` | Strictly monotonic integer indexing, SHA-256 chaining | $< 50\,\mu\text{s}$ per event |
| **Action Hub & 2PC** | `ActionIntentHub` | Two-phase commit state machine, four-eyes check, KMS signing | $< 5\,\text{ms}$ per transition |
| **Write-Back Sink** | `SimulatedWriteBackSink` | Idempotent operational mutations, receipts, chaos faults | $< 100\,\text{ms}$ execution |
| **WORM Anchoring** | `WORMAnchorService` | Periodic snapshot locking in immutable compliance storage | Hourly / per 100 txns |
| **Audit Walker** | `ContinuousAuditWalker` | Sequential cryptographic verification, tamper localization | $< 25\,\text{ms}$ per 1,000 entries |
| **Outcomes Ledger** | `DecisionOutcomesStore` | Propensity scores $e(X)$, multi-horizon forward tracking | Asynchronous batch ingestion |
| **OMCP & Specialist** | `GovernanceAuditorSpecialist` | Conversational audit queries, replay badge fallback | $< 500\,\text{ms}$ response |

All open architectural questions and technical context unknowns are fully resolved.
