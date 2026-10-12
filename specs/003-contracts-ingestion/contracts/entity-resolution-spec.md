# Single Client View (SCV) Entity Resolution Specification (ADR-008, S-07)

**Feature**: `003-contracts-ingestion` | **Date**: 2026-10-04  
**Context**: Palantir Citi Wealth & Global Investment Bank SCV Precedent × Anti-Circularity Hard Negatives  

This specification defines the exact two-stage hybrid linkage engine, comparison metrics, scoring cutoffs, and hub suppression thresholds for resolving fragmented trader records across MetaTrader 5 (MT5), Deriv Trader, and Deriv P2P (DP2P).

---

## 1. Mathematical Formulation

Let $A$ and $B$ represent two records from disparate operational systems.
We assess candidate pair $\gamma = \langle \gamma_1, \gamma_2, \dots, \gamma_k \rangle$ across comparison dimensions.

Under the **Fellegi-Sunter Model**:
$$\Lambda(\gamma) = \frac{P(\gamma \mid M)}{P(\gamma \mid U)} = \prod_{i=1}^k \frac{m_i(\gamma_i)}{u_i(\gamma_i)}$$
Where:
- $M$ is the set of true matching pairs (same physical person).
- $U$ is the set of unlinked pairs (different persons).
- Match Weight: $w(\gamma) = \log_2 \Lambda(\gamma) = \sum_{i=1}^k w_i(\gamma_i)$.

---

## 2. Comparison Dimensions & Weights

| Dimension | Attribute | Comparison Rule | $m$-probability | $u$-probability | Match Weight ($w_i$) |
|---|---|---|---|---|---|
| **D1** | Tax ID Hash (`tax_id_hash`) | Exact String Match | $0.995$ | $0.00001$ | $+16.6\text{ bits}$ |
| **D2** | Phone Hash (`phone_hash`) | Exact String Match | $0.920$ | $0.00005$ | $+14.2\text{ bits}$ |
| **D3** | Email Hash (`email_hash`) | Exact String Match | $0.950$ | $0.00002$ | $+15.5\text{ bits}$ |
| **D4** | Clean Name (`full_name_clean`) | Jaro-Winkler $\ge 0.92$ | $0.850$ | $0.00200$ | $+8.7\text{ bits}$ |
| | | Jaro-Winkler $[0.85, 0.92)$ | $0.700$ | $0.01500$ | $+5.5\text{ bits}$ |
| | | Jaro-Winkler $< 0.85$ | $0.050$ | $0.98300$ | $-4.3\text{ bits}$ |
| **D5** | Date of Birth (`dob`) | Exact Year + Month + Day | $0.980$ | $0.00010$ | $+13.3\text{ bits}$ |
| | | Same Year + Month, Day Diff $\le 1$ | $0.800$ | $0.00100$ | $+9.6\text{ bits}$ |
| **D6** | Device Fingerprint (`device_hash`) | Exact WebGL/Canvas Hash | $0.880$ | $0.00150$ | $+9.2\text{ bits}$ |

---

## 3. Decision Thresholds & Classification Rules

1. **Deterministic Match (Stage 1)**:
   - If $\text{ExactMatch}(\text{tax\_id\_hash}) \lor \text{ExactMatch}(\text{phone\_hash}) \lor \text{ExactMatch}(\text{email\_hash})$:
     - **Verdict**: `MATCH` (Deterministic).
     - **Confidence**: $1.00$.
     - **Action**: Merge records into `CanonicalClientEntity`.

2. **Probabilistic Linkage (Stage 2)**:
   - Candidate pairs generated via Blocking Rules:
     - Block 1: `block_on("first_name_initial", "dob")`
     - Block 2: `block_on("surname_prefix", "device_hash")`
     - Block 3: `block_on("country_code", "device_hash")`
   - **Match Weight Calculation**:
     - If $w(\gamma) \ge +12.0\text{ bits}$ ($\approx P(M \mid \gamma) \ge 0.95$):
       - Check Hub Suppression Filter (§4).
       - If passes hub check: `MATCH` (Probabilistic).
     - If $+6.0 \le w(\gamma) < +12.0\text{ bits}$:
       - **Verdict**: `POSSIBLE_MATCH` (Requires Human Review / EDD Flag).
     - If $w(\gamma) < +6.0\text{ bits}$:
       - **Verdict**: `NON_MATCH`.

---

## 4. Hub Suppression Filter (Crucial Anti-False-Merge Control)

### The Failure Mode
In naive graph and record linkage, high-degree shared identifiers (such as a single Android tablet shared by a family of 4, or an office Wi-Fi / carrier-grade NAT IP shared by 200 workers) cause transitive merges that collapse hundreds of innocent traders into one massive false fraud ring.

### The Algorithm
For any candidate pair $\langle A, B \rangle$ linked solely via `device_hash` or `ip_hash`:
1. Query in-memory degree $k$ of the linking attribute:
   $$k(\text{device\_hash}) = |\{\text{distinct tax\_id\_hash values observed on device\_hash}\}|$$
2. **Evaluation Rule**:
   - If $k(\text{device\_hash}) \ge 5$ OR $k(\text{ip\_hash}) \ge 10$:
     - **Action**: Suppress entity merge!
     - Tag edge as `is_shared_context = True`.
     - Output: Records $A$ and $B$ remain separate `canonical_client_id` entities.
     - Add property graph link: `(cl_A)-[:OPERATED_FROM_SHARED_DEVICE {degree: k}]->(device_D)`.
3. **Acceptance Threshold**:
   - False merge rate on shared family devices and shared office IPs must be $\le 0.1\%$ `[TARGET]`.
