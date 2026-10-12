# Research & Architectural Decisions: Client Fraud Sentinel / AML Transaction Monitoring (Module A / Slice S4)

**Feature**: `010-client-aml`  
**Created**: 2026-10-07  
**References**: `docs/brief/monitoring.md` `[BRIEF monitoring]`, `initial_plan.md` §5.4 `[BRIEF initial_plan.md]`, `docs/models_and_evals.md` §2, `.specify/memory/constitution.md`

---

## 1. Alert Triage & Queue Compression Architecture (2,000 Alerts $\to \le 50$ Cases)

### Context & Challenge
Per `docs/brief/monitoring.md`, financial crime teams receive ~2,000 alerts weekly, closing 95% as false positives. Manual triage burns out analysts while real criminals slip through. The system must compress 2,000 raw alerts down to $\le 50$ high-confidence investigation cases `[BRIEF monitoring]` retaining $\ge 90\%$ of true laundering events `[TARGET]`.

### Decision
Implement a **Calibrated Supervised Alert Triage Scorer** (`eios.aml.triage_scorer.AlertTriageScorer`) using regularized gradient boosting / calibrated logistic regression trained on analyst label history with simulated label noise (3–8% per `initial_plan.md` §5.4).
- **Feature Pipeline**:
  - `peer_z_score`: Deposit/withdrawal velocity deviation vs. peer cohort.
  - `kyc_recency_delta_hours`: Time elapsed since KYC approval ("72 hours after KYC approval" pattern `[BRIEF monitoring]`).
  - `roundtrip_risk_score`: Score from the sequence structuring detector.
  - `mule_ring_centrality`: Graph degree & cluster size from entity network.
  - `deposit_withdrawal_ratio`: Ratio of total withdrawn to total deposited.
  - `historical_alert_count`: Prior flagged events for this account.
- **Queue Ranking**: Computes calibrated risk probability $P(\text{illicit} \mid X)$; ranks top-$k$ alerts (capped at 50) into an executive worklist.

### Rationale
- High operational interpretability: Feature importances and individual SHAP/attribution weights explain to non-technical officers why an alert was prioritized.
- Strict sub-second execution: Scores 2,000 alerts in $< 200\text{ms}$ on CPU.
- Beating baseline: Non-linear interaction between KYC recency and micro-trading easily outperforms static single-variable threshold rules.

### Alternatives Considered
- *Deep Neural Network / TabNet*: Rejected due to high training latency, poor explainability for regulatory audits, and risk of overfitting on modest alert volumes.
- *Static Weighted Heuristic*: Rejected because it fails to capture non-linear interactions and cannot beat the naive baseline by $\ge 0.15$ PR-AUC on sealed seeds.

---

## 2. Cold-Start vs. Mature Account Behavioral Baselines

### Context & Challenge
New accounts have zero historical activity for deviation testing. Without a cold-start strategy, new signups either escape monitoring completely or trip false alarms on their very first deposit.

### Decision
Implement **Dual-Horizon Behavioral Baselines** (`eios.aml.peer_baseline.PeerBaselineEngine`):
1. **Cold-Start Cohort Baselines (< 5 transactions or < 7 days tenure)**:
   - Accounts are mapped to statistical peer buckets defined by `(country_tier, account_type, registration_channel)`.
   - Metrics tracked per cohort: median deposit amount ($\mu_{1/2}$), median velocity, 95th/99th percentile thresholds.
   - Deviations are scored against cohort robust scales: $\text{CohortScore} = \frac{x - \text{median}_{\text{cohort}}}{\text{MAD}_{\text{cohort}}}$.
2. **Mature Account Personalized Baselines ($\ge 5$ transactions and $\ge 7$ days tenure)**:
   - Computes robust per-customer statistics: Median Absolute Deviation (MAD) over personal rolling transaction windows.
   - Smooth exponential weighting: $\text{RiskScore} = \alpha \cdot \text{PersonalScore} + (1 - \alpha) \cdot \text{CohortScore}$, where $\alpha = \min(1.0, \frac{\text{txn\_count}}{20})$.

### Rationale
- Eliminates false-positive spikes during customer onboarding while detecting sudden outlier deposits that drastically exceed peer norms.
- Naturally accommodates legitimate high-net-worth accounts whose personal baseline scales up over time, preserving low FPR ($< 5\%$) on hard negatives.

---

## 3. Rapid Round-Trip Structuring & Micro-P&L Sequence Matcher

### Context & Challenge
Per `docs/brief/monitoring.md`: *"Client deposits $500, trades for 10 minutes with $0.01 profit, then withdraws. That's not trading - that's laundering. But our rules didn't catch it because the amounts were 'normal.'"*

### Decision
Implement a deterministic **Round-Trip Sequence Detector** (`eios.aml.roundtrip_detector.RoundTripDetector`):
- **Lifecycle Window**: Correlates deposit $\to$ trades $\to$ withdrawal request within a sliding window $\Delta t \le 72\text{ hours}$.
- **Near-Zero Market Risk Invariant**:
  $$\text{MarketExposureRatio} = \frac{|\sum \text{P\&L}|}{\text{TotalDeposited}} \le 0.02 \quad (\le 2\%)$$
- **Holding Velocity**: Median trade duration $\le 15\text{ minutes}$.
- **KYC Recency Factor**:
  $$\text{KYCBoost} = \begin{cases} 1.5 & \text{if } \text{time\_since\_kyc} \le 72\text{ hours} \\ 1.0 & \text{otherwise} \end{cases}$$
- **Score Formulation**:
  $$\text{Score}_{\text{roundtrip}} = \min\left(1.0, \left(1.0 - \frac{|\text{net P\&L}|}{\text{deposit}}\right) \times \left(\frac{\text{withdrawn}}{\text{deposited}}\right) \times \text{KYCBoost} \times \text{VelocityFactor}\right)$$

### Rationale
- Directly targets the exact money laundering typology specified in `docs/brief/monitoring.md`.
- Distinguishes authentic scalpers (who take directional exposure with variable P&L) from synthetic token traders seeking to disguise capital transfers.

---

## 4. Smurfing & Mule Ring Graph Clustering with Hub Suppression

### Context & Challenge
Organized financial crime syndicates coordinate across dozens of puppet accounts to deposit and withdraw small structured sums. However, naive shared-attribute graphs merge thousands of innocent users who happen to share a public airport Wi-Fi, university campus IP, or mobile CGNAT gateway.

### Decision
Implement a **Degree-Penalized Bipartite Entity Graph** (`eios.aml.mule_ring_detector.MuleRingDetector`) using NetworkX:
- **Entity Link Types**: Shared payment method token (`tok_pay_<hex16>`), hardware device hash (`tok_dev_<hex16>`), and external IP (`tok_ip_<hex16>`).
- **Hub Suppression Filter**:
  - Filter 1: Drop any attribute node marked with `is_shared_context = True` in the ontology.
  - Filter 2: Calculate degree distribution across all attribute nodes. Any node with $\text{degree} > 99\text{th percentile}$ (or $\text{deg} > 25$) is suppressed.
- **Edge Weight Penalization (Adamic-Adar / Resource Allocation)**:
  $$W(u, v) = \sum_{a \in N(u) \cap N(v)} \frac{1}{\log(1 + \text{deg}(a))}$$
- **Cluster Isolation**: Extract connected components with edge weight $W(u, v) \ge \tau_{\text{link}}$ ($0.75$).

### Rationale
- Isolates tightly coupled mule syndicates (shared credit card + hardware ID) while keeping public Wi-Fi false-merges strictly $< 5\%$ `[TARGET]`.
- Generates transparent, non-technical network explanations for compliance officers (e.g., "12 accounts linked by 2 private payment methods and 1 shared hardware ID").

---

## 5. Real-Time Pre-Withdrawal Fraud Intervention & Governed Proposals

### Context & Challenge
*"By the time we reconstruct a fraud timeline manually... the money is gone and the account is abandoned"* `[BRIEF monitoring]`. Detection must happen in real time during withdrawal processing.

### Decision
Implement the **Pre-Withdrawal Sentinel** (`eios.aml.withdrawal_sentinel.WithdrawalSentinel`):
- **Latency SLO**: Evaluates withdrawal requests in $< 2.0\text{s}$ p95 `[TARGET]` by querying pre-computed hot-state features from DuckDB in-memory tables.
- **Intervention Threshold**: If $\text{RiskScore}_{\text{withdrawal}} \ge 0.80$, the sentinel emits a Cloud KMS ECDSA P-256 signed `ActionIntentToken` proposal for `HoldWithdrawal`.
- **Constitutional Invariant (Principle II)**:
  - System NEVER auto-freezes customer balances.
  - Intent is created in `PENDING` state and queued for compliance officer review.
  - For high-severity / high-value withdrawals ($> \$2,500$), dual four-eyes human approval is enforced before execution against the simulated write-back sink.

---

## 6. Regulator-Ready SAR Composer & Statutory Citation Normalization

### Context & Challenge
Drafting a FinCEN or international FIU Suspicious Activity Report manually takes hours. All financial numbers must be 100% cited from deterministic tools (Principle I). Furthermore, legal statutory references (e.g., `31 CFR 1010.410`, `31 U.S.C. 5318(g)`, `Section 314(b)`) must NOT be flagged as ungrounded metrics by the Metric Auditor Gate.

### Decision
Implement the **SAR Composer with Statutory Normalizer** (`eios.aml.sar_composer.SARComposer`):
- **Standard Regulatory Sections**:
  1. *Suspect Information*: Client ID, KYC status, country, tenure, risk rating.
  2. *Summary of Suspicious Activity*: Typology categorization, total volume, date range.
  3. *Chronological Transaction Log*: Itemized deposit, trade, and withdrawal table with source citations.
  4. *Narrative Basis for Suspicion*: Explainable synthesis citing specific tool metrics and behavioral anomalies.
  5. *Statutory Regulatory Basis*: Legal provisions under which the report is filed.
- **Statutory Citation Normalizer**: A regex-driven parser that matches and white-lists recognized statutory law patterns:
  - `\b31\s*CFR\s*1010(?:\.\d+)?\b`
  - `\b31\s*U\.S\.C\.\s*5318\([a-z]\)\b`
  - `\b18\s*U\.S\.C\.\s*(?:1956|1957)\b`
  - `\bSection\s*314\([ab]\)\b`
  - `\bFinCEN\s*Form\s*111\b`
  Matches are tagged as `StatutoryReference` and exempted from the numerical metric audit.

---

## 7. Pre-Registered Naive Baseline for Principle VI Evaluation Gate

### Baseline Definition
Naive static threshold rules engine (`eios.aml.baseline.NaiveThresholdBaseline`):
- Flag if `amount > $10,000` (CTR threshold)
- OR `withdrawal_count_24h > 3`
- OR `time_between_deposit_and_withdrawal < 60 minutes`.

### Evaluation Target
In `FEIOS/tests/aml/test_aml_eval.py`:
- Supervised Alert Triage Scorer must beat `NaiveThresholdBaseline` by $\ge 0.15$ PR-AUC on sealed evaluation seeds `[CONSTITUTION Principle VI]`.
- False Positive Rate on legitimate high-volume traders (hard negatives) must be reduced by $\ge 30\%$ relative to the naive baseline `[TARGET]`.
