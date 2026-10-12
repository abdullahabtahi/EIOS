# Feature Specification: Partner & Affiliate Fraud Sentinel (Module B / Slice S3)

**Feature Branch**: `009-partner-fraud`  
**Created**: 2026-10-07  
**Status**: Draft  
**Authoritative References**: `docs/brief/fraud` `[BRIEF fraud]`, `initial_plan.md` §5.3 `[BRIEF initial_plan.md]`, `docs/models_and_evals.md` §4, `.specify/memory/constitution.md`  
**Input**: Partner and affiliate fraud detection system detecting opposite/mirror trading, multi-tier ring attribution, bonus abuse, client recycling, and bot/traffic fraud per `docs/brief/fraud` and `initial_plan.md` §5.3.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Coordinated Opposite & Mirror Trading Pair Detection (Priority: P1) 🎯 MVP

As an **Integrity / Fraud Investigator**,  
I want the system to detect pairs or groups of client accounts referred by different affiliates that take synchronized opposite positions or trade in lockstep,  
So that I can uncover collusive volume-harvesting and commission-splitting schemes before significant affiliate payouts occur.

**Why this priority**: Coordinated opposite trading is the highest-volume leakage channel in affiliate networks `[BRIEF fraud]`. Identifying trading pairs where net client P&L is approximately zero while commissions are extracted forms the core foundation of partner fraud detection.

**Independent Test**: Provide simulated trading records for accounts linked across multiple affiliates; query the fraud detection engine to verify it identifies collusive opposite/mirror pairs with exact correlation metrics (e.g., 89% timing overlap, inverse directional correlation), beating a naive rule baseline by $\ge 0.15$ PR-AUC on sealed holdouts without flagging legitimate hedgers.

**Acceptance Scenarios**:
1. **Given** two cohorts of referred clients under ostensibly unrelated partners taking inverse positions in the same instrument within a tight execution window ($< 15$ seconds),  
   **When** the pair correlation detector executes over the trading activity log,  
   **Then** the system flags the accounts as a coordinated opposite-trading cluster with computed timing overlap and net P&L symmetry.
2. **Given** legitimate institutional hedging clients who hedge portfolio risk across currencies,  
   **When** the correlation detector evaluates their trading history,  
   **Then** the system does NOT flag them as fraudulent, keeping the False Positive Rate bounded ($< 5\%$).

---

### User Story 2 - Multi-Tier Sub-Affiliate Ring Mapping & Master Partner Attribution (Priority: P1)

As a **Head of Partnerships / Compliance Lead**,  
I want to map referral network hierarchies up to 3 layers deep and attribute coordinated fraud rings back to the ultimate Master Partner / Sub-Affiliate ringleader,  
So that enforcement actions (commission freezes and contract terminations) target the ring organizer rather than just isolated puppet accounts.

**Why this priority**: Fraudulent partners routinely spawn throwaway sub-affiliates to insulate the master account from simple 1-hop rule triggers `[BRIEF fraud]`. Without multi-hop graph attribution, clawbacks miss the primary beneficiary.

**Independent Test**: Load a 3-layer sub-affiliate referral tree where sub-partners execute coordinated abuse; run referral-tree attribution and verify the graph traversal maps all subsidiary branches back to the true master partner with full lineage evidence.

**Acceptance Scenarios**:
1. **Given** a 3-tier affiliate tree where Level-3 sub-affiliates refer accounts engaging in bonus abuse and commission extraction,  
   **When** the network ring detector executes over the partner hierarchy graph,  
   **Then** the system traces all commission flows and referral links upstream to identify the root Master Partner and computes total ring exposure in USD.
2. **Given** a legitimate multi-level broker network with high-volume sub-affiliates,  
   **When** the graph engine evaluates the network,  
   **Then** high degree nodes are not penalized or misclassified as fraud rings due to hub-suppression filtering.

---

### User Story 3 - Client Quality & Bonus Abuse Scoring (Priority: P1)

As a **Partner Operations Manager**,  
I want an automated client quality scorer that detects "deposit $\to$ minimal micro-trading $\to$ immediate withdrawal" bonus harvesting patterns across a partner's client base,  
So that partner tiers, commission rates, and CPA qualification rules are adjusted according to genuine business value.

**Why this priority**: CPA and signup bonus structures are heavily gamed by syndicates generating dummy accounts that satisfy minimum qualification criteria and immediately exit `[BRIEF fraud]`.

**Independent Test**: Provide client lifecycle events across partner portfolios; verify the scorer assigns low client-quality scores ($< 0.20$) to accounts with high deposit-to-withdrawal velocity and negligible trading volume, and surfaces the aggregate abuse ratio per partner.

**Acceptance Scenarios**:
1. **Given** a partner referring 100 clients where 80% deposit the minimum qualifying threshold, execute a single micro-lot trade, and request withdrawals within 72 hours,  
   **When** the client quality engine calculates the partner's cohort metrics,  
   **Then** the partner is flagged with `HIGH_BONUS_ABUSE_RISK` and a client quality index $< 0.15$.
2. **Given** a partner referring active retail traders with distributed tenure and realistic deposit-to-volume ratios,  
   **When** evaluated by the quality scorer,  
   **Then** the partner achieves a normal quality rating ($\ge 0.75$) with zero bonus abuse flags.

---

### User Story 4 - Identity Clustering & Cross-Affiliate Client Recycling Detection (Priority: P2)

As a **Sentinel Fraud Analyst**,  
I want the system to detect when the same underlying individual or hardware cluster signs up repeatedly under different affiliate codes using pseudonymized Identity Cluster Keys (`tok_id_cluster_<hex16>`),  
So that multi-affiliate promotion recycling syndicates are identified without violating PII boundaries.

**Why this priority**: Fraud rings recycle the same client identities across different partner IDs to game introductory campaigns `[BRIEF fraud]`. Using deterministic cluster tokens preserves privacy while unmasking syndicate rings.

**Independent Test**: Simulate multi-account registrations across 5 affiliates sharing resolved hardware/IP/payment cluster keys; verify the recycling detector identifies the cluster and quantifies cross-affiliate overlap.

**Acceptance Scenarios**:
1. **Given** multiple client accounts registered under different partner IDs sharing the same `tok_id_cluster_<hex16>` entity key,  
   **When** the recycling detector inspects the onboarding and transaction stream,  
   **Then** the system groups the accounts into a recycled syndicate entity and flags all associated partners.
2. **Given** shared household or corporate network clients who share external IP addresses but have distinct verified KYC identity clusters,  
   **When** analyzed by the recycling engine,  
   **Then** the system distinguishes them from single-actor recycling syndicates and avoids false positive alarms.

---

### User Story 5 - Traffic & Bot Anomaly Detection (Priority: P2)

As a **Digital Marketing Compliance Specialist**,  
I want to identify unnatural click-to-lead-to-deposit conversion funnels and impossible conversion velocity outliers,  
So that bot-driven traffic and stolen-lead conversion fraud are flagged before affiliate commission payouts are disbursed.

**Why this priority**: Sophisticated affiliates manipulate web funnels, driving fake bot clicks or feeding stolen lead lists into partner links to claim high conversion incentives `[BRIEF fraud]`.

**Independent Test**: Feed clickstream and conversion events with simulated bot traffic patterns (e.g. 95% click-to-FTD conversion within 60 seconds); verify the traffic anomaly detector flags the distribution as statistically impossible relative to peer baselines.

**Acceptance Scenarios**:
1. **Given** an affiliate exhibiting an unnatural 92% click-to-deposit conversion rate with uniform latency distribution ($p < 0.001$ vs peer benchmark),  
   **When** the traffic anomaly engine processes daily funnel events,  
   **Then** the partner is flagged with `BOT_TRAFFIC_ANOMALY` and conversion velocity alerts.
2. **Given** a partner running a targeted high-converting offline seminar with genuine organic conversions,  
   **When** analyzed with peer variance bounds,  
   **Then** the system allows contextual justification without triggering blocking enforcement actions.

---

### User Story 6 - Explainable Investigation Dossier & Governed Action Intent Proposals (Priority: P2)

As a **Senior Compliance Officer / MLRO**,  
I want an explainable case dossier summarizing network evidence, commission exposure, and confidence scores, alongside a Cloud KMS ECDSA P-256 signed Action Intent proposal (`ClawbackCommission` or `SuspendPartner`),  
So that I can review and execute legally defensible enforcement actions under dual four-eyes approval without risk of autonomous write-back.

**Why this priority**: Compliance decisions have severe legal and financial consequences. The system must present complete audit evidence and adhere to Principle II (no autonomous write-back).

**Independent Test**: Trigger a fraud case creation for an identified syndicate; verify the OMCP tool generates a structured dossier and emits a signed `ActionIntentToken` requiring 2 distinct human signatures before execution against the simulated sink.

**Acceptance Scenarios**:
1. **Given** an investigation case with 5 supporting evidence artifacts and estimated financial exposure $>\$2,500$,  
   **When** the `PartnerFraudSpecialist` proposes an action intent `ClawbackCommission`,  
   **Then** the system generates a KMS-signed `ActionIntentToken` in `PENDING` status requiring dual four-eyes approval (`requires_dual_approval = True`).
2. **Given** a single officer attempting to execute a high-severity `SuspendPartner` intent,  
   **When** `execute_action` is called without the second distinct approver signature,  
   **Then** the system strictly raises `FourEyesApprovalRequiredError` and blocks execution.

---

### User Story 7 - Unsupervised Emerging Fraud Scheme Discovery & Continuous Learning (Priority: P3)

As a **Financial Crime Data Scientist**,  
I want the system to continuously mine transaction and network graphs for novel, emerging fraud typologies not captured by existing rule templates,  
So that the platform adapts to adversary evolution and improves detection precision over time.

**Why this priority**: Fraud rings continuously adapt techniques once existing rules become known `[BRIEF fraud]`. Unsupervised anomaly clustering surfaces novel topologies before losses scale.

**Independent Test**: Evaluate the emerging pattern miner on sealed holdout synthetic datasets containing novel unlabelled fraud typologies; verify the miner flags anomalous clusters with high purity.

**Acceptance Scenarios**:
1. **Given** a novel synthetic fraud typology (e.g. cyclic commission rebating across 4 intermediaries) absent from supervised training labels,  
   **When** the emerging scheme miner executes over historical graph snapshots,  
   **Then** the system isolates the anomalous sub-graph as a candidate typology with an explainable structural profile.

---

### Edge Cases

- **Cold-Start Partners**: A new affiliate with $< 5$ referred clients has insufficient history for statistical correlation. The system defaults to baseline monitoring and flags alerts only on deterministic KYC/identity collisions.
- **Micro-Hedging Volatility**: Sharp market news spikes causing simultaneous cross-client order placements in opposite directions are normalized using market-wide order flow volume to prevent spurious correlation alerts.
- **Cross-Jurisdiction Legal Privacy**: Data access for investigation dossiers must enforce role clearance markings (`PARTNER_COMMERCIAL`, `SENSITIVE_COMPLIANCE`, `PII`) so investigators only access fields authorized by their role clearance.
- **Deep Referral Recursion**: Circular referral loops (e.g. Partner A refers Partner B refers Partner A) must be detected and safely pruned during graph traversal to prevent infinite recursion.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute temporal and directional correlation across client trading pairs referred by different partners within sliding time windows ($[1, 60]$ seconds) `[BRIEF fraud]`.
- **FR-002**: System MUST identify mirror trading patterns where accounts execute identical instruments, lot sizes, and hold durations in lockstep.
- **FR-003**: System MUST calculate net position P&L vs. total affiliate commission extracted for suspected trading pairs to identify zero-sum commission harvesting.
- **FR-004**: System MUST maintain and traverse a multi-tier referral graph supporting up to 3 hierarchical sub-affiliate layers `[BRIEF fraud]`.
- **FR-005**: System MUST attribute aggregate fraud exposure, commission payouts, and sub-affiliate activities back to the root Master Partner using degree-penalized graph traversal.
- **FR-006**: System MUST evaluate client lifecycle velocity to calculate a bonus abuse score based on deposit-to-withdrawal latency and trading engagement volume.
- **FR-007**: System MUST calculate an aggregate Client Quality Index for every active partner, tracking client retention, trade distribution, and organic activity `[BRIEF fraud]`.
- **FR-008**: System MUST consume pseudonymized Layer 1 Identity Cluster Keys (`tok_id_cluster_<hex16>`) to detect client recycling across distinct partner IDs without unmasking raw PII.
- **FR-009**: System MUST calculate statistical conversion metrics (click $\to$ signup, signup $\to$ deposit) and flag distributions deviating from peer cohorts by $> 3.0$ standard deviations.
- **FR-010**: System MUST assemble comprehensive investigation dossiers aggregating transaction logs, network relationship graphs, commission history, and evidence citations.
- **FR-011**: System MUST emit Cloud KMS ECDSA P-256 signed `ActionIntentToken` objects for any proposed enforcement actions (`ClawbackCommission`, `SuspendPartner`, `HoldWithdrawal`) `[CONSTITUTION Principle II]`.
- **FR-012**: System MUST enforce dual four-eyes approval on high-severity action intents or financial exposures exceeding $\$2,500$ `[CONSTITUTION Principle II]`.
- **FR-013**: System MUST record all approved, rejected, and executed fraud actions in the append-only `Decision_Ledger` with tamper-evident SHA-256 hash chaining `[CONSTITUTION Principle II]`.
- **FR-014**: System MUST NOT allow any LLM to compute fraud risk scores, exposure dollars, or statistical p-values; all quantitative figures MUST originate from deterministic Ontology functions `[CONSTITUTION Principle I]`.
- **FR-015**: System MUST implement a naive rule-based baseline ("same instrument, opposite direction within $N$ seconds") and beat it by $\ge 0.15$ PR-AUC on sealed holdouts `[CONSTITUTION Principle VI]`.
- **FR-016**: System MUST support deterministic replay fallback for case explanations and OMCP tool responses during external LLM outages `[CONSTITUTION Principle VIII]`.
- **FR-017**: System MUST sanitize all outbound case summaries through the Semantic Egress Gate, replacing inflammatory accusations with objective compliance inquiry terminology.

---

### Key Entities

- **`PartnerFraudCase`**: The central investigation unit containing case ID, partner ID, primary typology, estimated financial exposure USD, confidence score, status, and supporting evidence references.
- **`TradingPairCorrelation`**: Quantifies collusive trading between two referred accounts, including instrument, execution time delta, lot size ratio, directional correlation coefficient ($-1.0$ to $1.0$), and net P&L.
- **`ReferralRingNode`**: Represents a node in the multi-tier affiliate hierarchy, capturing partner ID, tier level (1, 2, 3), parent partner ID, referred client count, aggregate ring commission, and master attribution link.
- **`BonusAbuseProfile`**: Summarizes client bonus harvesting metrics per partner, including fast-withdrawal ratio, median holding duration, micro-trade count, and composite abuse probability.
- **`RecyclingCluster`**: Groups client accounts linked across multiple affiliates by the deterministic entity key `tok_id_cluster_<hex16>`.
- **`TrafficAnomalySignal`**: Records conversion anomalies, including click volume, FTD count, conversion rate percentage, p-value vs peer cohort, and bot probability.
- **`ActionIntentToken`**: Cryptographically signed proposal containing intent ID, action type, parameters, severity, evidence refs, nonce, expiry, and multi-signature approval records.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System detects planted opposite-trading syndicates with $\ge 90\%$ recall while keeping false positive rate $< 5\%$ on hard-negative legitimate hedger portfolios `[TARGET]`.
- **SC-002**: Machine-learning pair detector beats naive threshold rule baseline by $\ge 0.15$ PR-AUC across sealed evaluation seeds `[CONSTITUTION Principle VI]`.
- **SC-003**: Referral-tree attribution correctly recovers the true Master Partner in $\ge 95\%$ of multi-tier ring topologies across 3 hierarchical layers `[TARGET]`.
- **SC-004**: Automated dossier assembly compiles evidence across 5+ data products into an OMCP investigation summary in $< 2.5$ seconds `[TARGET]`.
- **SC-005**: 100% of mutation actions (`ClawbackCommission`, `SuspendPartner`) are emitted as KMS-signed tokens and require human sign-off; zero autonomous write-backs occur `[CONSTITUTION Principle II]`.
- **SC-006**: 100% of quantitative figures in investigation dossiers cite registered ontology functions or provenance labels `[CONSTITUTION Principle I]`.
- **SC-007**: Turnaround time for multi-affiliate fraud investigations reduces from multi-week manual audits to same-day review `[BRIEF fraud]`.

---

## Assumptions

- **Data Availability**: Upstream L1 data products `partner_360`, `partner_network`, `trading_activity`, `commission_ledger`, `transactions_aml`, and `clickstream` are hydrated and available in the Hot State engine.
- **Pseudonymization**: Entity resolution produces consistent, deterministic `tok_id_cluster_<hex16>` keys at ingestion before data reaches the fraud module.
- **KMS Configuration**: Cloud KMS key ring or simulated local cryptographic provider is initialized with ECDSA P-256 signing keys.
- **Scope Boundary**: Client-level AML structuring and SAR filings for retail clients are scoped under Module A (F09); Module B focuses specifically on B2B partner, affiliate, and broker syndicate fraud.
