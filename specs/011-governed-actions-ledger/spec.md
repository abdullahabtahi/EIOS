# Feature Specification: Governed Actions & Decision Ledger (F10 / Slice S5)

**Feature Branch**: `011-governed-actions-ledger`  
**Created**: 2026-10-08  
**Status**: Draft  
**Authoritative References**: `initial_plan.md` §6.1, §6.2, §5.1, `docs/brief/monitoring.md`, `docs/brief/fraud.md`, `.specify/memory/constitution.md` (Principles I, II, IV, V, VI, VII, VIII)  
**Input**: User description: "Governed Actions & Decision Ledger: Two-phase commit protocol for agent mutation proposals, Cloud KMS ECDSA P-256 asymmetric signing, human-in-the-loop dual approval state machine (four-eyes authorization on High severity), upstream atomic sequence counter and cryptographic hash chain (ADR-017), simulated write-back sink with chaos fault injection, WORM chain-head anchoring, continuous cryptographic audit verification, and multi-horizon decision outcomes ledger for Doubly Robust AIPW counterfactual tracking."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Atomic Monotonic Sequencer & Cryptographic Hash Chain Ledger (Priority: P1) 🎯 MVP

As a **Lead Compliance Auditor & Security Officer**,  
I want every action proposal, human approval, and execution event stamped with an upstream atomic, strictly monotonic sequence number and chained cryptographically to the preceding record,  
So that the decision history is completely immutable, tamper-evident, and auditable, mathematically guaranteeing that no record can be secretly inserted, deleted, modified, or reordered.

**Why this priority**: Without an upstream monotonic sequence counter and cryptographic hash chain, streaming inserts into distributed analytical data stores cannot guarantee total ordering or detect sequence gaps. This is the foundational prerequisite for enterprise compliance and non-repudiation.

**Independent Test**: Submit a sequence of action proposals and approvals; verify that each event receives a strictly consecutive integer sequence number (`ledger_seq = 1, 2, 3...`) and that each entry contains the cryptographic hash of the preceding record ($H_i = \text{SHA-256}(H_{i-1} \parallel \text{seq}_i \parallel \text{payload}_i)$). Tampering with any byte of a historical entry or attempting out-of-order insertion must immediately fail cryptographic validation.

**Acceptance Scenarios**:

1. **Given** a newly initialized ledger,  
   **When** the first action proposal is recorded,  
   **Then** the sequencer assigns `ledger_seq = 1`, links to a pre-registered genesis hash anchor, computes the cryptographic digest, and appends the entry to the ledger.
2. **Given** a ledger with $N$ recorded entries,  
   **When** a new approval or execution event arrives,  
   **Then** the sequencer atomically increments `ledger_seq = N + 1`, retrieves the digest of entry $N$, binds the payload, and produces an unbroken cryptographic hash chain.
3. **Given** an attempt to insert an entry with a duplicate sequence number or a mismatching predecessor digest,  
   **When** processed by the sequencer,  
   **Then** the transaction is rejected with a sequence integrity error and logged to the security audit alert stream.

---

### User Story 2 - Governed Two-Phase Commit State Machine & Four-Eyes Authorization (Priority: P1)

As a **Chief Compliance Officer & Risk Manager**,  
I want all automated agent risk proposals to follow a strict two-phase commit lifecycle requiring authenticated human sign-offs, with high-severity actions strictly requiring two distinct approvers (Four-Eyes Authorization),  
So that AI agents can never autonomously alter financial balances, seize partner commissions, or freeze client accounts without explicit, dual human authorization.

**Why this priority**: Regulated financial institutions cannot permit autonomous write-back for severe operational mutations. Dual human authorization (Four-Eyes principle) is legally required by regulatory frameworks and Constitution Principle II.

**Independent Test**: Propose high-severity intents (`HoldWithdrawal`, `FreezeAccount`, `ClawbackCommission`, `SuspendPartner`) and medium-severity intents (`LaunchRetentionPlaybook`); verify that high-severity actions remain in `PENDING` status after a single approval and only transition to `APPROVED` when a second distinct authorized officer approves. Verify that execution attempts with fewer than two approvals fail unconditionally.

**Acceptance Scenarios**:

1. **Given** an AI agent emits a high-severity `HoldWithdrawal` action intent proposal with a valid Cloud KMS asymmetric signature,  
   **When** the first compliance officer submits an approval,  
   **Then** the token records the first approval signature and remains in `PENDING` status with policy tag `DUAL_APPROVAL_MANDATORY`.
2. **Given** a high-severity intent awaiting a second approver,  
   **When** the same approver attempts to sign a second time,  
   **Then** the system rejects the duplicate submission with an authorization validation error.
3. **Given** a high-severity intent awaiting a second approver,  
   **When** an execution attempt is made before a second distinct approver signs off,  
   **Then** the system raises a Four-Eyes Authorization error, blocking any write-back.
4. **Given** a high-severity intent with two distinct approvals from authorized roles,  
   **When** the second approval is recorded,  
   **Then** the intent status transitions to `APPROVED`, unlocking the commit execution phase.
5. **Given** a medium-severity action with financial impact below the fast-path budget threshold ($\le \$2,500.00$),  
   **When** a single authorized manager approves the intent,  
   **Then** the intent transitions directly to `APPROVED` under the policy fast-path.

---

### User Story 3 - Simulated Core Write-Back Sink with Chaos Fault Injection (Priority: P2)

As a **Forward-Deployed Systems Engineer**,  
I want approved action intents committed against a simulated core write-back sink that records realistic operational side-effects across core banking, affiliate payment gateways, and CRM systems,  
So that production-grade two-phase commit semantics, idempotency, and disaster recovery can be demonstrated and validated without mutating live external banking APIs.

**Why this priority**: Testing failovers, network splits, and compensation logic against real production core banking systems is dangerous. A dedicated simulated write-back sink provides isolated operational realism and allows intentional chaos fault injection.

**Independent Test**: Execute approved intents against the simulated write-back sink; verify that each execution produces a verifiable receipt with execution timestamp and external transaction ID. Verify that submitting duplicate execution calls returns the existing receipt without duplicate side-effects. Inject network timeout and lock collision faults; verify that transactions transition to `FAILED` or `ABORTED` with complete compensation audit logs.

**Acceptance Scenarios**:

1. **Given** an action intent in `APPROVED` status,  
   **When** the execution phase commits the action to the simulated write-back sink,  
   **Then** the sink records the state mutation in the execution registry, emits an execution receipt, and transitions the intent status to `EXECUTED`.
2. **Given** an action intent already in `EXECUTED` status,  
   **When** a client resubmits the execution request with the same idempotency key,  
   **Then** the sink returns the original execution receipt without creating duplicate transactions or double-booking financial records.
3. **Given** the simulated write-back sink is configured with an active chaos fault mode (e.g. simulated network timeout),  
   **When** an approved action attempts to commit,  
   **Then** the sink rejects the commit, transitions the action state to `ABORTED`, and records a compensation entry in the decision ledger.

---

### User Story 4 - WORM Chain-Head Anchoring & Continuous Cryptographic Audit Walker (Priority: P2)

As an **External Regulatory Auditor**,  
I want the system to periodically anchor the cryptographic chain-head digest to immutable WORM (Write-Once-Read-Many) storage and run a continuous background audit walker across the entire ledger,  
So that we have verifiable mathematical proof that historical ledger entries have never been altered, truncated, or forged.

**Why this priority**: Even a hash chain stored in a database can theoretically be rewritten if an attacker compromises the underlying database table and recalculates hashes from the point of edit forward. Anchoring the chain-head to immutable WORM storage locks the root digest against any future retroactive alteration.

**Independent Test**: Generate a series of ledger entries and execute an hourly WORM checkpoint anchor; run the continuous audit walker across the ledger; verify that it returns a 100% integrity health status. Artificially alter a single character in a historical payload or delete a middle sequence record; verify that the audit walker detects the exact sequence index of corruption and raises a critical integrity alarm.

**Acceptance Scenarios**:

1. **Given** an active ledger with sequential entries,  
   **When** the periodic anchoring checkpoint runs,  
   **Then** the latest `ledger_seq` and `current_hash` are bundled into a WORM checkpoint record and anchored to immutable storage with a non-modifiable retention policy.
2. **Given** an untampered ledger and verified WORM anchors,  
   **When** the audit walker inspects the ledger,  
   **Then** it sequentially recalculates and verifies every hash link, validates sequence continuity, confirms match with WORM anchors, and outputs an audit report with 100% integrity score.
3. **Given** a ledger where a historical record at `ledger_seq = K` has been modified by an adversary,  
   **When** the audit walker executes,  
   **Then** it identifies the hash mismatch at sequence $K$, pinpoints the exact corrupted transaction ID, and generates a critical tamper alert.

---

### User Story 5 - Multi-Horizon Decision Outcomes Ledger & AIPW Counterfactual Logging (Priority: P3)

As a **Lead Decision Scientist**,  
I want every action proposal to record the agent's estimated propensity score $e(X)$, the observed causal context, and manager override decisions, followed by multi-horizon forward actuals (30, 60, and 90 days) in a dedicated decision outcomes ledger,  
So that offline causal machine learning models can execute Doubly Robust Augmented Inverse Probability Weighting (AIPW) to recalibrate policy thresholds without observational confounding bias.

**Why this priority**: Because human managers selectively approve actions only on perceived high-risk accounts ("confounding by indication"), naive comparison of approved vs. unapproved accounts yields biased estimates. Recording propensity scores and counterfactual context at decision time enables mathematically rigorous offline causal inference.

**Independent Test**: Ingest action intent proposals with propensity scores and simulated forward outcomes (retained revenue, actual churn, clawback recoveries at 30, 60, and 90 days); verify that records in `decision_outcomes_ledger` capture complete treatment assignment, propensity scores, and manager override flags.

**Acceptance Scenarios**:

1. **Given** an agent proposes an action intent,  
   **When** the proposal is logged,  
   **Then** the system records the treatment assignment, the calculated propensity score $e(X) \in (0, 1)$, and the full causal context vector in the decision outcomes ledger.
2. **Given** an approved or rejected action where a human officer alters the proposed playbook or budget,  
   **When** the decision is recorded,  
   **Then** the ledger stamps `manager_override_flag = TRUE` along with the authorized officer's documented reason.
3. **Given** elapsed forward horizons (30, 60, 90 days),  
   **When** outcome reconciliation executes,  
   **Then** observed financial impacts (retained revenue, realized losses, operational costs) are linked back to the original intent ID, enabling unbiased counterfactual evaluation.

---

### User Story 6 - Canonical OMCP Governance Tools & Conversational Auditor Specialist (Priority: P3)

As a **Platform User & Compliance Investigator**,  
I want to inspect action intent statuses, review approval queues, trigger human approvals, and verify cryptographic ledger integrity through canonical OMCP tools and conversational agent interfaces,  
So that governance controls are seamlessly integrated across both analytical dashboards and AI assistant conversations with deterministic fallback under outages.

**Why this priority**: Human operators need natural, intuitive access to the governance state machine. Integrating governance tools into OMCP ensures consistent security enforcement and enables conversational agents to explain action statuses clearly.

**Independent Test**: Invoke governance tools via OMCP (`propose_action`, `approve_action`, `execute_action`, `get_ledger_audit_status`, `verify_hash_chain`); verify role-based permissions enforcement. Simulate an external LLM gateway outage; verify that the system returns deterministic, verified audit status responses marked with `[REPLAY]` badges.

**Acceptance Scenarios**:

1. **Given** an authorized compliance officer interacting with the conversational interface,  
   **When** asking to inspect pending approvals for a high-risk case,  
   **Then** the conversational agent queries `get_intent_status` and displays the pending dual-approval status, token validity, and evidence citations.
2. **Given** an auditor querying ledger integrity,  
   **When** invoking `verify_hash_chain`,  
   **Then** the tool executes verification across the cryptographic ledger and returns verified sequence length, head hash, and audit health status.
3. **Given** an external service outage,  
   **When** a user queries governance audit records,  
   **Then** the system falls back to a deterministic cached summary stamped with a `[REPLAY]` badge pursuant to Constitution Principle VIII.

---

### Edge Cases

- **Concurrent Double-Approval Race Condition**: Two officers submit approvals simultaneously; the transactional state machine must process them sequentially, verifying that two distinct user IDs are recorded without duplicate count.
- **Token Expiry During Review**: An intent token expires (15 minutes elapsed) while sitting in the approval queue; any subsequent approval or execution attempt must be rejected with `TokenExpiredError` and require a fresh proposal.
- **Single-Approver Trying to Sign Twice**: An approver attempts to sign a high-severity action with their own credentials twice; system rejects the second submission and requires a distinct identity.
- **Simulated Core Outage & Network Split**: The simulated write-back sink experiences an injected fault during execution; the two-phase commit state machine aborts the transaction, marks the intent `ABORTED`, and records a compensation entry without dangling state.
- **Out-of-Order Sequencer Submission**: Distributed processes attempt to write entries with non-sequential counters; the atomic sequencer enforces serialized monotonic increments, guaranteeing that no gaps or out-of-order writes enter the ledger.
- **Catastrophic History Tampering**: An attacker edits an arbitrary historical row; the audit walker immediately flags the discrepancy between $H_{k-1} \parallel \text{seq}_k \parallel \text{payload}_k$ and $H_k$, outputting the exact corrupted sequence number.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST assign an upstream atomic, strictly monotonic integer sequence number (`ledger_seq`) to each recorded ledger event prior to analytical persistence `[CONSTITUTION Principle II]`.
- **FR-002**: System MUST compute a cryptographic hash chain linking each ledger entry to its predecessor ($H_i = \text{SHA-256}(H_{i-1} \parallel \text{ledger\_seq}_i \parallel \text{payload\_digest}_i)$) with a registered genesis anchor for `ledger_seq = 1` `[CONSTITUTION Principle II]`.
- **FR-003**: System MUST implement a governed two-phase commit protocol for all agent mutation proposals: Phase 1 (Propose intent $\to$ `PENDING`), Phase 2 (Human approval $\to$ `APPROVED`), Phase 3 (Commit to simulated write-back sink $\to$ `EXECUTED` or `ABORTED`) `[CONSTITUTION Principle II]`.
- **FR-004**: System MUST enforce dual distinct authenticated human approvals (Four-Eyes Authorization) for all High-severity action types (`HoldWithdrawal`, `FreezeAccount`, `ClawbackCommission`, `SuspendPartner`) before transitioning to `APPROVED` `[CONSTITUTION Principle II]`.
- **FR-005**: System MUST support policy-governed single-approver fast-path for operational action types (`LaunchRetentionPlaybook`, `AdjustPartnerTier`) when financial impact is below the pre-registered threshold ($\le \$2,500.00$) `[TARGET]`.
- **FR-006**: System MUST enforce Cloud KMS asymmetric signature verification (`ECDSA_P256_SHA256`) and single-use nonce validation for all action intent tokens, rejecting replayed or expired tokens ($> 15$ minutes) `[CONSTITUTION Principle II]`.
- **FR-007**: System MUST route approved action executions to a Simulated Core Write-Back Sink that isolates external side effects, returns typed execution receipts, and supports idempotency keys `[CONSTITUTION Principle II]`.
- **FR-008**: System MUST support controllable chaos fault injection in the simulated write-back sink (e.g. simulated network timeout, core ledger lock collision) to verify error handling and compensation tracking `[TARGET]`.
- **FR-009**: System MUST perform periodic chain-head checkpoint anchoring to an immutable WORM storage model simulating Google Cloud Storage Object Retention Lock in Compliance Mode `[CONSTITUTION Principle II]`.
- **FR-010**: System MUST execute a continuous cryptographic audit walker that sequentially verifies sequence monotonicity, validates all hash links, checks WORM anchor proofs, and returns a verified ledger health score `[CONSTITUTION Principle II]`.
- **FR-011**: System MUST log counterfactual decision context at proposal time (propensity score $e(X)$, causal context vector, manager override flags) in `decision_outcomes_ledger` `[BRIEF, initial_plan.md §6.2]`.
- **FR-012**: System MUST record multi-horizon observed forward actuals (30-day, 60-day, 90-day retention and loss metrics) against recorded action intents for downstream Doubly Robust AIPW flywheel recalibration.
- **FR-013**: System MUST expose governed OMCP tools (`propose_action`, `approve_action`, `execute_action`, `get_ledger_audit_status`, `verify_hash_chain`) with role-based security enforcement `[CONSTITUTION Principle IV]`.
- **FR-014**: System MUST maintain deterministic replay fallback responses with `[REPLAY]` badging for governance status queries during LLM or gateway outages `[CONSTITUTION Principle VIII]`.

---

### Key Entities

- **`ActionIntentToken`**: Represents a non-autonomous mutation proposal emitted by an agent, containing unique intent ID, action type, parameters, severity, evidence references, nonce, timestamps, Cloud KMS signature, approval records, propensity score, and causal context.
- **`ApprovalRecord`**: Captures an individual human sign-off, containing approver ID, approver role, authenticated timestamp, and review comments.
- **`LedgerEntry`**: The core immutable audit log record containing atomic sequence number (`ledger_seq`), predecessor digest (`prev_hash`), current digest (`current_hash`), event type, canonical payload digest, timestamp, and WORM anchor reference.
- **`ExecutionReceipt`**: Emitted by the simulated write-back sink upon successful commitment, containing receipt ID, intent ID, external reference number, execution status, and simulated settlement latency.
- **`WORMAnchorCheckpoint`**: Represents a periodic checkpoint snapshot locked in immutable storage, containing checkpoint sequence, chain-head sequence ID, anchored root hash, retention expiration timestamp, and compliance lock status.
- **`DecisionOutcomeRecord`**: Captures the counterfactual evaluation record linking action intents to forward outcomes, including propensity score $e(X)$, causal context, manager override flag, and 30/60/90-day observed actuals.
- **`AuditVerificationReport`**: Output of the continuous audit walker, detailing total entries verified, sequence continuity status, hash chain validity, WORM anchor matches, detected corruption indices (if any), and overall integrity score.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of recorded ledger entries form an unbroken cryptographic hash chain with zero sequence gaps on sequential inserts `[TARGET]`.
- **SC-002**: 100% of High-severity actions require two distinct authenticated approvals; zero unauthorized or premature executions succeed `[CONSTITUTION Principle II]`.
- **SC-003**: 100% of mutation proposals carry Cloud KMS ECDSA P-256 asymmetric signatures; replayed nonces and expired tokens are rejected with 100% accuracy `[CONSTITUTION Principle II]`.
- **SC-004**: The continuous audit walker detects single-byte payload tampering or sequence deletion with 100% precision, pin-pointing the exact corrupted sequence index `[TARGET]`.
- **SC-005**: Simulated write-back execution completes in $< 100$ ms with full idempotency on duplicate submissions `[TARGET]`.
- **SC-006**: 100% of proposed action intents log propensity scores $e(X)$ and causal contexts into `decision_outcomes_ledger`, eliminating confounding by indication in downstream analysis `[TARGET]`.
- **SC-007**: 100% of governance query operations maintain deterministic fallback capability stamped with `[REPLAY]` badges under simulated LLM outages `[CONSTITUTION Principle VIII]`.

---

## Assumptions

- **IdP Authentication**: Approver identity is provided by the calling environment's authenticated context (e.g. JWT claims / caller role) and is never spoofable via request payload parameters.
- **Simulated Cloud Storage WORM**: In local and test execution environments, the Cloud Storage Object Retention Lock (Compliance mode) is simulated via an in-memory / file-based immutable WORM abstraction that enforces append-only retention rules.
- **Asymmetric Key Provider**: Cloud KMS ECDSA P-256 signing is executed via the `KMSActionSigner` abstraction (using local cryptography providers in testing and Google Cloud KMS in deployed environments).
- **Simulated Sink Scope**: The write-back sink records operational transactions in a dedicated hot-state table (`simulated_writeback_ledger`) without connecting to live third-party bank clearinghouses.
