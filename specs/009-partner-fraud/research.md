# Research & Technology Decisions: Partner & Affiliate Fraud Sentinel (Module B / Slice S3)

**Feature**: `specs/009-partner-fraud/` (Module B / Slice S3)  
**Standard**: QuantumBlack Horizon Architecture × Palantir Foundry Kinetic Ontology × Google Cloud Reference Architecture  
**Authoritative References**: `docs/brief/fraud` `[BRIEF fraud]`, `initial_plan.md` §5.3, `docs/models_and_evals.md` §4

---

## 1. Coordinated Opposite & Mirror Trading Pair Detection

### Context & Challenge
Trading platforms with 5,000 affiliates and millions of transactions encounter collusive syndicates where referred clients open opposing positions (e.g. Account A buys 10 lots EUR/USD while Account B sells 10 lots EUR/USD within 5 seconds) to harvest affiliate volume commissions with zero market risk `[BRIEF fraud]`. Pairwise comparison across all trades is computationally $O(N^2)$, which is infeasible for real-time detection.

### Decision
Implement a two-stage **Time-Bucketed Candidate Pruning & Statistical Anti-Correlation Filter**:
1. **Stage 1 (Candidate Hashing)**: Partition all trades into overlapping 30-second sliding time buckets indexed by `(symbol, expiry_bucket)`. Only trade pairs co-occurring within the same bucket and referred by distinct partners enter candidate evaluation.
2. **Stage 2 (Bilateral Correlation Scoring)**: For candidate pairs, compute:
   - **Directional Anti-Correlation**: $r_{\text{dir}} = \text{sign}(S_i) \cdot \text{sign}(S_j)$ (where $-1.0$ is perfect opposite trading, $+1.0$ is lockstep mirror trading).
   - **Volume Symmetry**: $\text{Sym}(V_i, V_j) = 1.0 - \frac{|V_i - V_j|}{\max(V_i, V_j)}$.
   - **Timing Proximity Score**: $T_{\text{score}} = \exp(-\Delta t / \tau)$ with $\tau = 5.0\text{s}$.
   - **Net Zero-Sum P&L**: Ratio of combined net client P&L to total extracted affiliate commission:
     $$\text{ZeroSumRatio} = 1.0 - \min\left(1.0, \frac{|P\&L_i + P\&L_j|}{\text{Commission}_i + \text{Commission}_j + \epsilon}\right)$$
   - **Composite Collusion Score**:
     $$\text{CollusionIndex} = w_1 \cdot |r_{\text{dir}}| + w_2 \cdot \text{Sym} + w_3 \cdot T_{\text{score}} + w_4 \cdot \text{ZeroSumRatio}$$

### Alternatives Considered
- **Naive Brute-Force Cartesian Product**: $O(N^2)$ cross join across trading table. Rejected due to latency ($> 45\text{s}$) and memory overflow on 100k+ trades.
- **Graph Neural Network (GNN) on Trade Edges**: Dynamic edge classification. Rejected for POC/S3 due to high training overhead, lack of offline refutation guarantees, and risk of non-deterministic inference latency.

---

## 2. Multi-Tier Sub-Affiliate Ring Traversal & Master Partner Attribution

### Context & Challenge
Affiliate syndicates frequently create 3-tier sub-affiliate structures (`Master Partner -> Sub-Affiliate -> Tier-2 -> Referred Accounts`) to insulate the ringleader from detection. Standard single-hop queries fail to attribute the full financial volume back to the root beneficiary `[BRIEF fraud]`.

### Decision
Implement a **Directed Hierarchical NetworkX Referral Traversal Engine with Degree-Penalized Attribution**:
1. Build directed graph $G = (V, E)$ from `partner_network` where edges represent `parent_id -> child_id` referral links with `layer \in {1, 2, 3}`.
2. Apply **Hub Suppression**: High-degree legitimate master brokers (e.g., regional IBs with $> 500$ sub-brokers) have edge weights penalized by inverse log degree to prevent legitimate marketing hubs from falsely triggering ring clustering.
3. For any flagged transaction or bonus abuse event, traverse upstream to the root master partner:
   $$\text{MasterExposure}(P_{\text{root}}) = \sum_{v \in \text{Descendants}(P_{\text{root}})} \text{CommissionEarned}(v) \cdot \text{AbuseRatio}(v)$$
4. Cycle Detection: Enforce strict cycle detection; any circular referral loop (e.g., $A \to B \to A$) is detected and pruned, raising an integrity alert.

### Alternatives Considered
- **Neo4j Cypher Traversal**: Requires dedicated external database container, violating in-memory warm-start architecture.
- **Recursive SQL Common Table Expressions (CTEs)**: DuckDB supports recursive CTEs, but NetworkX offers degree-penalized graph analysis, topological sorting, and cycle breaking out-of-the-box in deterministic Python.

---

## 3. Client Quality & Bonus Abuse Scorer

### Context & Challenge
Partners game introductory CPA bonuses by referring puppet clients who deposit the minimum threshold (e.g. $100), execute a single micro-lot trade to qualify the partner for a $200 CPA bounty, and immediately withdraw all funds `[BRIEF fraud]`.

### Decision
Implement a deterministic **Lifecycle Velocity & Quality Index**:
1. Compute per-client lifecycle features:
   - `DepositToWithdrawalLatencyHours`: Time elapsed between first deposit and withdrawal request.
   - `TurnoverToDepositRatio`: $\text{TotalVolumeUSD} / \text{TotalDepositedUSD}$.
   - `TradeCount30d`: Total trades executed within first 30 days.
   - `RetentionDay30Active`: Boolean indicator of activity past day 30.
2. Calculate the **Partner Client Quality Index (CQI)**:
   $$\text{CQI}(P) = \alpha \cdot \overline{\text{TurnoverRatio}} + \beta \cdot \text{ActiveRetentionRate}_{30d} - \gamma \cdot \text{FastWithdrawalRate}_{72h}$$
   Normalized to $[0.0, 1.0]$. A partner with $\text{CQI} < 0.20$ is automatically categorized as `HIGH_BONUS_ABUSE_RISK`.

### Alternatives Considered
- **Unsupervised K-Means on Account Lifecycles**: Unstable cluster boundaries across synthetic runs; difficult for compliance officers to explain to regulators. Deterministic multi-factor scoring provides 100% auditable thresholds.

---

## 4. Cross-Affiliate Client Recycling & Identity Clustering

### Context & Challenge
Syndicates recycle identical physical individuals across multiple affiliate codes to harvest introductory bonuses multiple times. Exposing raw PII to the fraud engine violates privacy regulations and Constitution Principle IV.

### Decision
Leverage the **Layer 1 Identity Cluster Key (`tok_id_cluster_<hex16>`)**:
1. Upstream entity resolution ingests hashed IP, device fingerprint, payment method tokens, and identity credentials, emitting a single deterministic cluster key `tok_id_cluster_<hex16>`.
2. The fraud sentinel evaluates the bipartite graph between `partner_id` and `tok_id_cluster_<hex16>`.
3. If an identity cluster maps to $\ge 2$ distinct affiliate hierarchies within a 90-day window, the accounts are aggregated into a `RecyclingSyndicate` entity.

### Alternatives Considered
- **Direct PII Comparison**: Comparing raw emails/phones. Strictly forbidden by Constitution Principle IV.
- **Fuzzy String Matching in Fraud Engine**: Leaks PII across security boundaries and is computationally slow.

---

## 5. Traffic & Bot Anomaly Detection

### Context & Challenge
Affiliates use automated headless scripts or purchased click farms to generate artificial traffic and fake registrations, seeking to manipulate conversion incentive tiers `[BRIEF fraud]`.

### Decision
Implement a **Beta-Binomial Peer Cohort Dispersion Test**:
1. For each partner $i$, observe clicks $N_i$ and first-time deposits $K_i$.
2. Model baseline conversion across regional peer affiliates as $\text{Beta}(\alpha, \beta)$.
3. Compute the empirical Bayes posterior conversion rate and p-value.
4. If observed conversion rate exceeds peer mean by $> 3.5\sigma$ and registration-to-deposit latency shows unnatural zero-variance spikes, flag as `BOT_TRAFFIC_ANOMALY`.

---

## 6. Naive Baseline & Evaluation Protocol (Constitution Principle VI)

### Pre-Registered Naive Baseline
- **Baseline Rule**: Flag any two clients referred by different partners who execute trades in the same currency pair in opposing directions (BUY vs SELL) within $30.0$ seconds of each other.
- **Evaluation Criteria**: The machine-learning / multi-factor pair collusion detector MUST beat the naive rule baseline by:
  $$\Delta \text{PR-AUC} \ge 0.15 \text{ on sealed evaluation holdouts}$$
  while keeping False Positive Rate on hard-negative legitimate hedgers $< 5.0\%$.
