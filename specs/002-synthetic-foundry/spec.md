# Feature Specification: Synthetic Enterprise Data Foundry (F01)

**Feature Branch**: `002-synthetic-foundry`
**Created**: 2026-10-02
**Status**: Draft
**Input**: User description: "F01-synthetic-foundry: Layer 0 deterministic generators with hard negatives, sealed typologies, and placebo edges. Scope per initial_plan.md §3, §8 (slice S0), and docs/synthetic_data_strategy.md. Must implement the Palantir Foundry Pilot pattern, outputting to exact L1 contracts."

**Constitution references**: Principle I (LLMs Never Compute Metrics - via providing the raw truth), Principle IV (Data as a Product - via L1 contract adherence), Principle V (Provenance and Labelling - via ground truth buckets), Principle VI (Eval-First, Anti-Circularity - via hard negatives, seed splits, and placebo edges), Principle VIII (Deterministic Fallback and Operability), and Red-Line Tests RL-1..RL-7.

**Labelling regime**: figures in this document carry the tags defined in Principle V and `initial_plan.md` §0.2. `[BRIEF]` anchors to client requirements in `docs/brief/*`. `[ILLUSTRATIVE]` marks generated noise, scenarios, or unanchored values. `[TARGET]` marks an acceptance threshold we commit to measuring. `[ASSUMPTION]` marks an engagement default that a later phase may revise. `[SPIKE]` marks unverified technical claims.

## Users of the Platform

- **FDE Team Lead**: Controls the `sealed` seed manifest and verifies that the CI eval-harness correctly scores release candidates without leaking data.
- **Data Scientist / Modeler**: Uses `dev` and `validation` seeds to train the hazard models, graph suppressors, and causal engines against seeded baselines.
- **Data Engineer**: Uses the generated output streams to test the L1 ingestion spine, contract validators, dead-letter queues, and DuckDB warm-start procedures.
- **Evaluation Engineer**: Verifies that the Eval-Only ground-truth bucket enables automated scoring for Red-Line tests (RL-1..RL-7) and baseline comparisons.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deterministic generation with sealed isolation (Priority: P1)

The FDE Team Lead runs a single command to generate the entire broker history based on a specific `seed` manifest. The generator creates `dev` data for local work, but when the CI pipeline runs a release candidate, it uses a `sealed` seed with distribution shift and unannounced typologies. The true labels (which accounts are actually fraud, which causal edges are placebos) are written to a secure bucket that the L3 Reasoning Mesh and models at inference can never access.

**Why this priority**: Without determinism, debugging is impossible. Without sealed isolation, the system violates Principle VI (Anti-Circularity) and models will overfit to the generated data.

**Independent Test**: Generate data using seed `A`. Verify cryptographic hashes of outputs. Generate again with seed `A` and verify hashes match perfectly. Generate with seed `B` and verify outputs differ. Verify IAM permissions on the ground-truth bucket deny read access to the agent service account.

**Acceptance Scenarios**:

1. **Given** a fixed `manifest.yaml` `{seed, git_sha, spec_hash, dataset_hash, generator_versions}`, **When** the foundry executes, **Then** it produces byte-identical Parquet files across multiple runs.
2. **Given** a foundry execution, **When** it completes, **Then** the truth labels are deposited in the Eval-Only Bucket, completely separate from the mocked Pub/Sub topics.
3. **Given** an L3 Agent execution in `dev` or `stage`, **When** the agent attempts to read the Eval-Only bucket, **Then** the IAM configuration actively denies the request.
4. **Given** a release-candidate CI run, **When** evaluating models, **Then** it executes against `sealed` seeds containing distribution shifts and ≥ 2 unannounced typologies not present in model-author documentation.

---

### User Story 2 - A fragmented, Global Federated Customer Master (Priority: P1)

A Data Engineer testing the L1 Ingestion spine needs a realistic feed of clients, partners, devices, and payment methods. The `gen_client` generator does not output a perfect single table; it outputs fragmented records simulating MT5, Deriv Trader, and DP2P systems, containing deliberate duplicates and conflicting fields to exercise probabilistic Entity Resolution.

**Why this priority**: If L0 produces perfectly clean, unified entities, the L1 Entity Resolution service has nothing to resolve, defeating the purpose of the Palantir Foundry Pilot pattern.

**Independent Test**: Inspect the output of `gen_client`; verify that the same underlying UUID is represented by multiple disparate records (e.g., matching name and device hash but differing email) across the simulated systems.

**Acceptance Scenarios**:

1. **Given** the `gen_client` generator, **When** it runs, **Then** it produces a unified internal entity universe but emits fragmented, system-specific representations simulating MT5, Deriv Trader, and DP2P.
2. **Given** a generated client, **When** downstream generators (`gen_aml`, `gen_partner`) create events, **Then** they reference the correct fragmented system IDs (e.g., MT5 login ID), requiring downstream systems to resolve them.
3. **Given** shared device/IP networks, **When** generating client telemetry, **Then** it injects benign shared-context profiles (e.g., expatriate families sharing a tablet or IP) to serve as hard negatives for entity resolution and graph linking.

---

### User Story 3 - Module A (Client Sentinel / AML) stream with hub suppression noise (Priority: P1)

An AML Modeler needs a realistic stream of deposits, withdrawals, and trades. The stream must contain ~2,000 baseline rules-engine alerts per week, calibrated so ~95% are false positives `[BRIEF]`. It must contain the anchored 47-account syndicate `[BRIEF]`, the round-trip laundering pattern ($500 → 10 min → $0.01 → withdraw) `[BRIEF]`, and the "activity within 72 hours of KYC approval" pattern `[BRIEF]`. Crucially, it must contain "hub suppression" hard negatives: hundreds of benign clients sharing a single carrier-NAT or campus IP.

**Why this priority**: Necessary to prove the graph engine can correctly suppress false hubs and not merge 500 legitimate users into a massive fraud ring.

**Independent Test**: Inspect the `gen_aml` output; count the frequency of the round-trip typology and verify the presence of the 47-account ring in the ground truth. Verify at least one IP is shared by >100 unlinked legitimate accounts.

**Acceptance Scenarios**:

1. **Given** the AML generator, **When** it runs, **Then** it embeds exactly one 47-account syndicate matching the `[BRIEF]` parameters into the dataset.
2. **Given** the AML generator, **When** it runs, **Then** it embeds the `$500 → 10 min → $0.01 → withdraw` pattern `[BRIEF]`.
3. **Given** the AML generator, **When** generating account lifecycle events, **Then** it embeds a burst of structuring or laundering activity concentrated within 72 hours of KYC approval `[BRIEF]`.
4. **Given** the AML generator, **When** generating network data, **Then** it injects at least one CGNAT, campus, or office IP shared by ≥ 500 legitimate, unlinked clients (hard negative).
5. **Given** transaction streams, **When** generating benign volume, **Then** it injects legitimate high-volume traders whose velocity mimics structuring (hard negative).

---

### User Story 4 - Executive Synthesis causal chain with Placebo Edges & Driver Decomposition (Priority: P1)

The Data Science team needs data that proves the Executive Synthesis Engine can perform true causal reasoning across four domains (Competitive → Partner → Client → Financial). The generator creates a structural causal model where a competitor payout increase causes partner mix shifts, dropping client quality, and reducing LTV. It injects a "Placebo Edge" (true effect = 0) that statistically correlates but has no causal weight. It also provides ground-truth driver attribution summing to 100%.

**Why this priority**: Required to enforce Principle III (Honest Uncertainty) and the causal-evidence gate. The system must reject the placebo edge and attribute drivers accurately.

**Independent Test**: Read the `gen_causal_truth` ground-truth file; verify it explicitly tags exactly one edge as a `PLACEBO` with a structural equation effect of exactly 0.0. Verify driver attribution sums to 100%.

**Acceptance Scenarios**:

1. **Given** the causal generator, **When** it evaluates the 4-domain chain, **Then** the structural equations correctly propagate the shock from Competitive events to Financial metrics.
2. **Given** the causal generator, **When** configuring the DAG, **Then** it embeds at least one Placebo Edge that is statistically correlated in the data but has zero true effect in the structural equation.
3. **Given** the causal truth generation, **When** label noise is applied, **Then** 3-8% `[ASSUMPTION]` of the analyst ground-truth labels are flipped to simulate ambiguity.
4. **Given** a forecast variance scenario, **When** the causal truth generates driver attribution, **Then** the ground-truth counterfactual drivers sum to 100% exactly (e.g., 40% competitive, 35% partner, 25% operational `[BRIEF]`).

---

### User Story 5 - Partner Fraud, Churn Radar & Comms Security (Priority: P2)

The Fraud and Partner Management teams need partner integrity data, churn radar signals, and security test corpora. The generator creates a 3-tier sub-affiliate ring (7 partners / 23 sub / 184 clients) `[BRIEF]`, opposite/mirror trading (23 pairs, 0.89 timing correlation) `[BRIEF]`, bonus abuse (35% share `[ILLUSTRATIVE]`), client recycling, traffic/bot conversion outliers ("12 partners" `[BRIEF]`), 5 families of churn signals, seasonal dips, and regional cohort churn events. It also injects prompt-injection payloads into support comms to test Red-Line RL-6.

**Why this priority**: Required for Modules B and C, proving multi-tier attribution, hazard model resilience, and LLM security safeguards.

**Independent Test**: Verify the presence of the 3-tier ring, mirror trading pairs, and 12 traffic-fraud partners in the ground truth. Verify that 8% of partners experience a 30-day "dip" that recovers. Verify prompt-injection strings exist in `partner_comms`.

**Acceptance Scenarios**:

1. **Given** `gen_partner`, **When** it runs, **Then** it embeds the `[BRIEF]` 3-tier ring (7 master partners, 23 sub-affiliates, 184 clients).
2. **Given** `gen_partner`, **When** simulating trading, **Then** it generates 23 opposite/mirror trading pairs with 0.89 timing correlation `[BRIEF]` and net P&L ≈ 0 while commission accrues.
3. **Given** `gen_partner`, **When** generating affiliate traffic, **Then** it injects 12 partners with impossible click-to-signup conversion rates and bot traffic `[BRIEF]`.
4. **Given** `gen_partner`, **When** generating commissions, **Then** it embeds bonus abuse patterns (deposit → minimal activity → withdrawal, 35% share `[ILLUSTRATIVE]`).
5. **Given** `gen_partner_churn`, **When** generating time-series signals, **Then** it embeds 5 signal families (login decay, referral velocity, conversion, ticket sentiment, competitor language) with seasonal dips (8% share, 30-day recovery) and a regional cohort disengagement event.
6. **Given** `partner_comms` telemetry, **When** generating tickets and emails, **Then** it injects adversarial prompt-injection payloads to evaluate Red-Line test RL-6.

---

### User Story 6 - Enterprise Operations & Financial Telemetry (Priority: P2)

The Executive and Platform teams need operational and financial feeds to test cross-domain synthesis and data platform monitoring. The generator creates `financial_pnl`, `competitor_benchmarks`, and `platform_operations` feeds, linking financial metrics organically to client trading volumes and injecting operational shocks.

**Why this priority**: Enables end-to-end multi-domain synthesis without leaving P&L and infrastructure operational data as disconnected stubs.

**Independent Test**: Inspect `financial_pnl` and `platform_operations`; verify revenue and costs correlate with client trades and commission payouts. Verify at least one major operational latency/incident shock is planted.

**Acceptance Scenarios**:

1. **Given** `gen_financial`, **When** generating P&L data, **Then** revenue, cost, margin, and LTV cohorts derive organically from client trade volume and partner commission payouts.
2. **Given** `gen_competitive`, **When** generating market intel, **Then** competitor payout and promo shifts are tagged with generic aliases (e.g., "Competitor X"), never real company names.
3. **Given** `gen_operational`, **When** generating platform telemetry, **Then** it outputs latency, incident tickets, and dispute logs, containing background benign noise and exactly one planted operational shock.

---

### Edge Cases

- **Contract Violation**: If a generator attempts to write a record that fails the Pydantic schema of the L1 spine, the generator must log the violation and CRASH immediately. Silently dropping or mutating bad records is forbidden.
- **Cross-Domain Identifier Mismatch**: If the Partner generator attempts to reference a Client ID that does not exist in the Global Entity Universe, it must raise a referential integrity error during generation.
- **Sealed Seed Leakage**: If a developer attempts to generate a `sealed` dataset on a local machine without overriding the CI environment flag, the generation script must refuse to run.
- **Placebo Edge Discovery**: If the statistical correlation of a placebo edge naturally falls to zero due to small sample size, the generator must retry or inject synthetic correlation to ensure the L3 causal gate has to work to reject it.
- **Distribution Shift Drift**: If a `sealed` seed shifts distributions beyond the acceptable range of the L1 Pydantic contracts, generation must abort to prevent invalid schema breaches.

## Requirements *(mandatory)*

### Functional Requirements

**Architecture, Seed Splits & Anti-Circularity**

- **FR-001**: The Foundry MUST use a deterministic pseudo-random number generator (PRNG) strictly seeded by a versioned Manifest file containing `{seed, git_sha, spec_hash, dataset_hash, generator_versions}`.
- **FR-002**: Two executions of the Foundry with the identical Manifest MUST yield byte-identical Parquet outputs, verified by a cryptographic SHA-256 hash `[TARGET]`.
- **FR-003**: The Foundry MUST provide configuration profiles for three explicit seed tiers: `dev` (free local use), `validation` (CI model selection), and `sealed` (release-candidate CI evaluation).
- **FR-004**: The `sealed` seed generation MUST only execute in the CI/CD pipeline on release candidates, enforced by environment checks.
- **FR-005**: `sealed` seed runs MUST inject systematic distribution shifts (varied volume, seasonality, and noise levels) relative to `dev` seeds.
- **FR-006**: `sealed` seed runs MUST embed at least two (≥ 2) novel fraud or churn typologies that are completely withheld from model-author documentation to test unsupervised novelty discovery.
- **FR-007**: The Foundry MUST write all simulated telemetry (the "mock" data) to files or topics formatted identically to target production systems.
- **FR-008**: The Foundry MUST write all ground-truth labels (planted typologies, placebo tags, true causal graphs, driver splits) exclusively to an isolated Eval-Only GCS bucket.
- **FR-009**: The Foundry MUST NOT use any real Deriv production data or real PII; all names, emails, and identifiers MUST be synthetically generated (e.g., via `Faker`).
- **FR-010**: All generated records MUST pass the Pydantic schema contracts defined for the Layer 1 Ingestion spine before emission; a validation failure MUST halt the generator.

**Global Entity Universe (`gen_client`)**

- **FR-011**: `gen_client` MUST generate a unified, internal pool of `ClientAccount`, `Partner`, `Device`, `IPAddress`, and `PaymentMethod` entities.
- **FR-012**: The generator MUST project these unified entities into fragmented, system-specific representations simulating MT5, Deriv Trader, and DP2P.
- **FR-013**: The generator MUST inject intentional identity duplicates (e.g., same name and device, different email) to exercise L1 probabilistic entity resolution.
- **FR-014**: The generator MUST inject benign shared-context profiles (e.g., expatriate families sharing a tablet or IP, business users with multiple payment cards) to serve as hard negatives for entity resolution.
- **FR-015**: Downstream generators MUST exclusively pull foreign keys (Client IDs, Partner IDs) from this unified universe to ensure absolute referential integrity.
- **FR-016**: `gen_client` MUST output feeds mapped to data products `client_360`, `client_funnel`, and `device_network_graph`.

**Module A AML & Transactions (`gen_aml`)**

- **FR-017**: `gen_aml` MUST generate transaction volumes and telemetry calibrated to yield ~2,000 baseline rules-engine alerts per week `[BRIEF]`.
- **FR-018**: The generated alerts MUST be calibrated such that ~95% are benign false positives `[BRIEF]`.
- **FR-019**: The generator MUST inject the exactly anchored `[BRIEF]` 47-account linked syndicate ring topology.
- **FR-020**: The generator MUST inject the exactly anchored `[BRIEF]` round-trip laundering typology: $500 deposit → 10 min hold → $0.01 micro-trade → withdrawal.
- **FR-021**: The generator MUST inject the anchored `[BRIEF]` KYC pattern: a burst of suspicious transaction activity concentrated within 72 hours of KYC approval.
- **FR-022**: The generator MUST inject hard negatives simulating legitimate high-volume traders whose velocity mimics structuring.
- **FR-023**: The generator MUST inject "hub-suppression" noise: at least one CGNAT, campus, or office IP shared by ≥ 500 entirely unrelated, benign clients.
- **FR-024**: The true membership of the 47-account ring and round-trip event IDs MUST be written to the Eval-Only bucket.
- **FR-025**: `gen_aml` MUST output feeds mapped to data products `transactions_aml`, `trading_activity`, and `compliance_cases`.

**Module B Partner Fraud (`gen_partner`)**

- **FR-026**: `gen_partner` MUST generate a background population of 5,000 affiliates `[BRIEF]` with referral trees and commission ledgers.
- **FR-027**: The generator MUST inject the anchored `[BRIEF]` multi-tier ring: 7 master partners, 23 sub-affiliates, and 184 clients across 3 referral layers.
- **FR-028**: The generator MUST inject 23 opposite/mirror trading pairs `[BRIEF]` with 0.89 timing correlation `[BRIEF]` where net client P&L approaches zero while affiliate commission extracted is high.
- **FR-029**: The generator MUST inject bonus abuse sequences: deposit → minimal activity → withdrawal, accounting for 35% of bonus payouts `[ILLUSTRATIVE]`.
- **FR-030**: The generator MUST inject "client recycling" patterns where the same devices/identities are re-registered under different affiliates.
- **FR-031**: The generator MUST inject 12 partners with impossible click-to-signup conversion rates and bot traffic `[BRIEF]`.
- **FR-032**: The generator MUST inject hard negatives: 40 legitimate hedgers, 12 introducing broker (IB) portfolios with opposite positions, and 15 genuine high-volume referrers `[ILLUSTRATIVE]`.
- **FR-033**: The true membership of the 3-tier ring, mirror pairs, and fraudulent partners MUST be written to the Eval-Only bucket.
- **FR-034**: `gen_partner` MUST output feeds mapped to data products `partner_360`, `partner_referral_tree`, and `commission_ledger`.

**Module C Partner Churn & Comms (`gen_partner_churn`)**

- **FR-035**: The generator MUST generate 5 families of time-series signals per brief: login decay, referral velocity, conversion rates, ticket sentiment, and competitor language mentions.
- **FR-036**: The generator MUST inject competitor poaching signals using generic aliases (e.g., "Competitor X"), never real brand names like Exness/XM (Principle V).
- **FR-037**: The generator MUST inject "seasonal dip" hard negatives: 8% of partners who go dormant for 14-30 days and recover after 30 days `[ILLUSTRATIVE]`.
- **FR-038**: The generator MUST inject at least one regional/segment cohort event: a systemic drop in partner activity across 8 partners in a specific region with a 14-day lag `[ILLUSTRATIVE]`.
- **FR-039**: The generator MUST simulate comms text containing poaching language (4% share `[ILLUSTRATIVE]`) including hard NLP cases with sarcasm and negation.
- **FR-040**: The generator MUST inject adversarial prompt-injection payloads into comms tickets to support automated CI evaluation of Red-Line test RL-6.
- **FR-041**: The true binary churn outcomes and cohort event IDs MUST be written to the Eval-Only bucket.
- **FR-042**: `gen_partner_churn` MUST output feeds mapped to data products `partner_engagement_signals` and `partner_comms`.

**Financial, Competitive & Operational Telemetry (`gen_financial`, `gen_competitive`, `gen_operational`)**

- **FR-043**: `gen_financial` MUST generate revenue, trading fees, commission expenses, net margin, and LTV cohorts organically driven by client trading and partner commissions, outputting to `financial_pnl`.
- **FR-044**: `gen_competitive` MUST generate competitor events (spread changes, payout adjustments, promotional campaigns) tagged with generic competitor aliases, outputting to `competitor_benchmarks`.
- **FR-045**: `gen_operational` MUST generate platform metrics (service latency, dispute counts, incident tickets) containing benign background noise and exactly one planted operational shock, outputting to `platform_operations`.

**Executive Synthesis & Causal Truth (`gen_causal_truth`)**

- **FR-046**: The generator MUST construct a 4-domain causal chain: Competitive (payout increase) → Partner (mix shift) → Client (quality fall) → Financial (LTV decline).
- **FR-047**: The generator MUST use structural equations to simulate the true causal effects propagating through this chain.
- **FR-048**: The generator MUST inject ≥ 1 Placebo Edge into the DAG (a statistical correlation with zero true structural causal effect, requiring p > 0.05 on the placebo refuter to pass).
- **FR-049**: The generator MUST provide ground-truth driver attribution decomposing a forecast miss into drivers that sum to exactly 100% (e.g., 40% competitive, 35% partner, 25% operational `[BRIEF]`).
- **FR-050**: The generator MUST apply label noise to analyst decision labels, flipping 3-8% `[ASSUMPTION]` at random to simulate human ambiguity and prevent models from achieving 100% precision.
- **FR-051**: The true structural equations, edge coefficients, placebo edge IDs, and driver shares MUST be written to the Eval-Only bucket.

### Key Entities & Data Product Mappings

- **Manifest**: Configuration object `{seed, git_sha, spec_hash, dataset_hash, generator_versions}` ensuring byte-identical reproducibility.
- **Global Entity Universe**: Unified UUID pool (`ClientAccount`, `Partner`, `Device`, `IPAddress`, `PaymentMethod`, `Competitor`) prior to system projection.
- **Eval-Only Ground Truth**: Isolated datasets mapping entity IDs to true labels, structural DAG equations, and placebo tags, accessible only by CI/eval harness.
- **Data Product Mappings**:
  - `client_360`, `client_funnel`, `device_network_graph` ← `gen_client`
  - `transactions_aml`, `trading_activity`, `compliance_cases` ← `gen_aml`
  - `partner_360`, `partner_referral_tree`, `commission_ledger` ← `gen_partner`
  - `partner_engagement_signals`, `partner_comms` ← `gen_partner_churn`
  - `financial_pnl` ← `gen_financial`
  - `competitor_benchmarks` ← `gen_competitive`
  - `platform_operations` ← `gen_operational`
  - Eval-Only Truth Bucket ← `gen_causal_truth`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Run determinism test: 2 executions of the pipeline with the identical seed manifest yield 100% identical SHA-256 hashes on all output Parquet files before any code is merged `[TARGET]`.
- **SC-002**: 100% of generated records pass the L1 Pydantic ingestion schemas without modification or data loss `[TARGET]`.
- **SC-003**: 100% of simulated PII (names, emails) is verified to be synthetically generated (e.g., matching known `Faker` dictionaries) via an automated scan `[TARGET]`.
- **SC-004**: Identity and Access Management (IAM) simulation confirms that L3 service accounts possess exactly `0` read permissions on the Eval-Only ground truth bucket `[TARGET]`.
- **SC-005**: The Eval-Only ground truth files explicitly list the members of the 47-account ring, the 7/23/184 partner ring, the 12 traffic-fraud partners, and the exact ID of the placebo edge.
- **SC-006**: The hub-suppression hard negative is verified to exist: a query against the generated data returns ≥ 1 IP address shared by ≥ 500 otherwise unlinked clients.
- **SC-007**: A deliberate mutation of a Pydantic contract causes the generator to fail immediately and loudly, verifying FR-010.
- **SC-008**: The driver attribution ground truth is verified to sum to exactly 100.0% across all decomposed root-cause categories.
- **SC-009**: At least two (≥ 2) novel typologies are confirmed present in the `sealed` dataset and absent from the `dev` dataset ground truth.

## Assumptions

- `[ASSUMPTION]` Python `Faker` and `numpy` random states are sufficient for byte-for-byte deterministic generation, provided internal sorting and multithreading are strictly controlled.
- `[ASSUMPTION]` Generation runs locally or in CI as a batch process, emitting Parquet files, which can later be replayed to Pub/Sub for streaming simulations.
- `[ASSUMPTION]` The label noise threshold of 3-8% accurately reflects institutional manual-review ambiguity levels.
- The tag vocabulary and provenance rule are as defined by constitution Principle V and `docs/synthetic_data_strategy.md` §2.
- The Red-Line tests RL-1..RL-7 are defined in `docs/models_and_evals.md` §6; F01 provides the synthetic data and adversarial payloads required to evaluate them.
- No real customer data, mobile device data, or third-party proprietary datasets will be used to seed the generators.

