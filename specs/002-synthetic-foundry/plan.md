# Implementation Plan: Synthetic Enterprise Data Foundry (F01)

**Branch**: `002-synthetic-foundry` | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-synthetic-foundry/spec.md`

## Summary

Feature F01 delivers the **Synthetic Enterprise Data Foundry (Layer 0)**, establishing the seeded, deterministic data foundation for the entire Enterprise Intelligence Operating System (EIOS) per `initial_plan.md` §3 (L0), §8 (Slice S0), and `docs/synthetic_data_strategy.md`. F01 implements the Palantir Foundry Pilot pattern: standing up a realistic stand-in that proves the platform end-to-end against exact Layer 1 contracts so that nothing above L1 knows the data is synthetic.

Technical approach:

- **Deterministic Generator Mesh (`eios.foundry`)**: Seven specialized sub-generators (`gen_client`, `gen_aml`, `gen_partner`, `gen_partner_churn`, `gen_financial`, `gen_competitive`, `gen_operational`, `gen_causal_truth`) initialized from a master `numpy.random.SeedSequence` with PCG64 PRNG bit-generators.
- **Strict Provenance & Manifest Hashing**: Every run produces a versioned `manifest.yaml` recording seeds, code git SHA, generator versions, and a Merkle SHA-256 root dataset hash (`FR-001`, `FR-002`, `SC-001`).
- **Contract-Checked at Generation**: Every record batch is validated against Layer 1 Pydantic schemas before writing. Any validation failure halts generation loudly (`FR-010`, `SC-007`).
- **Global Entity Universe & Fragmented Projections**: A unified internal pool of physical persons, devices, and payment methods is projected into fragmented representations simulating MetaTrader 5, Deriv Trader, and DP2P, containing deliberate duplicate identities to test L1 Entity Resolution (`FR-011`–`FR-016`).
- **Brief-Anchored Typologies & Hard Negatives**: Embeds the 47-account syndicate ring, round-trip laundering ($500 $\rightarrow$ 10 min $\rightarrow$ $0.01), 72h post-KYC bursts, carrier-NAT hub suppression noise (>500 accounts on shared IP), 3-tier partner rings (7/23/184), mirror trading (0.89 correlation, 23 pairs), 12 bot-traffic partners, 5 churn signal families, seasonal dip hard negatives (8%), regional cohort churn shocks, and adversarial prompt-injection payloads (`FR-017`–`FR-0- **Structural Causal Model & Placebo Treatment Refuters**: Simulates a 4-domain causal chain (Competitive $\rightarrow$ Partner $\rightarrow$ Client $\rightarrow$ Financial) and injects at least one Placebo Edge (true effect = 0, $p > 0.05$) to enforce honest uncertainty, alongside ground-truth driver attribution summing to 100.0% (`FR-046`–`FR-051`).
- **Palantir Foundry Data Layer Semantics**: Incorporates dataset transaction metadata, deterministic schema snapshots, and input/output lineage tracking (`storage/lineage.py`), mirroring Foundry's Multimodal Data Plane (MMDP) architecture (`docs/foundry.md` §1).
- **Streaming Ingestion Bridge & S-07 Breach Injections**: Provides a Pub/Sub stream replayer (`replay.py`) with configurable velocity, and a dedicated test injector (`noise/breach_injector.py`) for seeded contract breaches and duplicate identities to exercise Layer 1 Dead-Letter Queues (DLQs) and Entity Resolution.
- **Anti-Circularity Isolation (ADR-015)**: Three seed tiers (`dev`, `validation`, `sealed`), 3–8% label noise, and complete deposition of ground truth exclusively to an isolated Eval-Only bucket blocked from L3 Reasoning Mesh access (`SC-004`).

## Technical Context

**Language/Version**: Python 3.11+ (aligned with F00 platform standard).

**Primary Dependencies**: `numpy>=1.26.0`, `pyarrow>=15.0.0`, `polars>=0.20.0`, `pydantic>=2.6.0`, `faker>=24.0.0`, `pyyaml>=6.0.0`, `google-cloud-pubsub>=2.19.0` (for stream replay). Tooling: `pytest` with `pytest-cov`, `ruff`, `mypy`. Rationale and alternatives documented in [research.md](./research.md).

**Storage**: Local Parquet files partitioned by date/domain topic (`data/raw/*`), isolated evaluation ground truth files in `fixtures/eval_truth/` (local) and `gs://<project>-eval-truth/` (cloud). Dataset-level lineage records in `_lineage.json`. No direct database writes in L0.

**Testing**: `pytest` covering unit, contract, and integration tiers under `tests/`; determinism tests verifying identical SHA-256 Merkle roots; Pydantic contract compliance suite; IAM isolation simulation; coverage gate $\ge 80\%$ `[TARGET]`.

**Target Platform**: Cloud Run batch jobs / CI runners (Ubuntu/Debian) and developer workstations (macOS/Linux).

**Project Type**: Reusable core library (`eios.foundry`) and CLI utility (`eios.foundry.cli`).

**Performance Goals**: Generate 1,000,000 synthetic records in $< 60$ seconds on standard developer hardware `[TARGET]`.

**Constraints**:
- Byte-for-byte identical output across multiple executions with the same manifest (`SC-001`).
- Zero real customer PII; 100% synthetic names and identifiers (`SC-003`).
- Hard crash on Layer 1 schema violation (`SC-007`).
- Zero read access for L3 Reasoning Mesh to the Eval-Only ground-truth bucket (`SC-004`).
- `sealed` seeds blocked from local execution without explicit CI release-candidate flag (`FR-004`).

**Scale/Scope**: 7 generators, 15 data products, 5,000 partners, 10,000 base clients, ~250,000 transactions/run (`dev` profile).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Principle / Constraint | Pre-research | Post-design |
|---|---|---|---|
| **G1** | **I. LLMs never compute business metrics.** L0 provides deterministic ground truth metrics via data products; no LLM is used to compute numbers. | PASS | PASS: Generators use deterministic PRNG equations; numbers flow via governed Parquet/PubSub contracts. |
| **G2** | **II. No autonomous write-back.** L0 is a generator emitting telemetry; it exposes no mutation API or write-back paths. | PASS | PASS: Outputs to read-only mock data directories; ground truth stored in eval-only storage. |
| **G3** | **III. Honest uncertainty & Causal Gate.** L0 generates structural causal equations and embeds Placebo Edges (true effect = 0, $p > 0.05$). | PASS | PASS: `FR-048`, `contracts/eval-ground-truth.schema.json`, and `research.md` (R-08). |
| **G4** | **IV. Data as a product, Ontology access.** L0 validates all output against L1 Pydantic contracts; breaches crash the generator immediately. | PASS | PASS: `FR-010`, `contracts/generator-output-catalog.md`, `SC-002`, `SC-007`. |
| **G5** | **V. Provenance and labelling.** Every figure carries a tag; runs are bound to manifest hashes. Real broker names are strictly prohibited. | PASS | PASS: `manifest.schema.json` Merkle hash; generic competitor aliases ("Competitor X") enforced (`FR-044`). |
| **G6** | **VI. Eval-first, anti-circularity (NON-NEGOTIABLE).** Seed tiers (`dev`, `validation`, `sealed`), hard negatives, 3–8% label noise, sealed typologies, and IAM-isolated truth bucket. | PASS | PASS: `contracts/seed-split-policy.md`, `SC-004`, `SC-009`, `FR-005`, `FR-006`. |
| **G7** | **VII. Specialised agents & decoupled pipelines.** L0 batch generation is strictly decoupled from streaming and downstream inference. | PASS | PASS: Emits discrete Parquet batches replayed asynchronously to Pub/Sub. |
| **G8** | **VIII. Deterministic fallback & operability.** Deterministic PRNG with SeedSequence guarantees exact replayability across all platforms. | PASS | PASS: `numpy.random.PCG64` with sorted output partitions ensures byte-identical Parquet (`SC-001`). |
| **G9** | **Secrets & Identity.** Ground truth bucket isolated via IAM; no credentials in repo. | PASS | PASS: IAM access matrix defined in `seed-split-policy.md` (§2). |
| **G10** | **Validation at boundaries.** Every generated batch validated against L1 Pydantic contracts before emission. | PASS | PASS: `TypeAdapter` batch validation in `eios.foundry.contracts`. |
| **G11** | **Open decisions stay open.** L0 does not pin or depend on LLM models, frontend stack, or metric engine choice. | PASS | PASS: L0 outputs standard Parquet tables and JSON ground truth only. |
| **G12** | **Red-Line test readiness.** L0 injects test corpora for RL-5 (synthetic PII) and RL-6 (prompt injections in comms). | PASS | PASS: `FR-040`, `SC-003`, `data-model.md` §4.5. |

Result: 100% PASS on all gates. The Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-synthetic-foundry/
├── spec.md                     # Feature specification (v2, 51 FRs, 9 SCs)
├── plan.md                     # This file (/speckit-plan output)
├── research.md                 # Phase 0 architectural & mathematical decisions
├── data-model.md               # Phase 1 data entities and schemas
├── quickstart.md               # Phase 1 runnable validation scenarios
├── contracts/
│   ├── manifest.schema.json
│   ├── eval-ground-truth.schema.json
│   ├── generator-output-catalog.md
│   └── seed-split-policy.md
├── checklists/
│   └── requirements.md         # Passed quality checklist
└── tasks.md                    # Created by /speckit-tasks (Phase 2)
```

### Source Code (repository root)

```text
src/eios/foundry/
├── __init__.py
├── cli.py                      # Single entry-point CLI for generation & verification
├── manifest.py                 # Manifest loading, validation, and Merkle hash computation
├── rng.py                      # Master SeedSequence & PCG64 stream management
├── universe.py                 # gen_client: Physical universe & fragmented projections
├── contracts.py                # Pydantic v2 batch validation integration
├── replay.py                   # Pub/Sub streaming replay engine for Layer 1 ingestion
├── generators/
│   ├── __init__.py
│   ├── client.py               # gen_client: Funnel, devices, IPs, duplicates
│   ├── aml.py                  # gen_aml: 47-account ring, $500 round-trip, hub noise
│   ├── partner.py              # gen_partner: 7/23/184 ring, mirror trading, 12 bot partners
│   ├── churn.py                # gen_partner_churn: 5 signal families, dips, cohort shocks
│   ├── financial.py            # gen_financial: P&L, commissions, trading revenues
│   ├── competitive.py          # gen_competitive: Competitor events with generic aliases
│   ├── operational.py          # gen_operational: Latency, dispute tickets, operational shock
│   └── causal_truth.py         # gen_causal_truth: 4-domain SCM, placebo edge, driver split
├── noise/
│   ├── __init__.py
│   ├── hard_negatives.py       # CGNAT hub IP, legitimate hedgers, seasonal churn dips
│   ├── label_noise.py          # 3-8% analyst ambiguity flipping
│   ├── prompt_injections.py    # Adversarial comms corpus for Red-Line RL-6
│   └── breach_injector.py      # Seeded contract-breach & duplicate injection for S-07 / DLQ testing
└── storage/
    ├── __init__.py
    ├── parquet_writer.py       # Deterministic sorted Parquet writer
    ├── lineage.py              # Dataset transaction & lineage tracking metadata writer
    └── eval_truth_store.py     # Isolated ground truth writer with IAM deny checks

tests/foundry/
├── conftest.py
├── test_determinism.py         # SC-001: Byte-identical SHA-256 Merkle root verification
├── test_contracts.py           # SC-002, SC-007: L1 Pydantic schema validation & hard crash
├── test_pii_anonymity.py       # SC-003: Faker PII scan and brand name prohibition
├── test_iam_isolation.py       # SC-004: Eval-only bucket access restriction simulation
├── test_planted_typologies.py  # SC-005: 47-account ring, 7/23/184 ring, mirror pairs, placebos
├── test_hub_suppression.py     # SC-006: Hub IP degree >= 500 stress test
├── test_driver_attribution.py  # SC-008: Forecast driver decomposition sums to 100.0%
├── test_sealed_tier.py         # SC-009: Sealed tier CI gate and novel typology presence
├── test_lineage.py             # Foundry dataset lineage metadata verification
└── test_replay.py              # Pub/Sub streaming replay verification
```

## Implementation Milestones (for `/speckit-tasks`)

1. **M1: Core Deterministic Infrastructure** (`manifest.py`, `rng.py`, `contracts.py`, `storage/parquet_writer.py`, `storage/lineage.py`).
2. **M2: Global Entity Universe & Fragmented Silos** (`universe.py`, `generators/client.py`, `noise/hard_negatives.py`).
3. **M3: Domain Telemetry Generators** (`generators/aml.py`, `partner.py`, `churn.py`, `financial.py`, `competitive.py`, `operational.py`).
4. **M4: Causal Modeling, Placebo Edges & Isolated Ground Truth** (`generators/causal_truth.py`, `storage/eval_truth_store.py`, `noise/label_noise.py`, `noise/prompt_injections.py`).
5. **M5: Ingestion Bridge, Test Injectors & Verification Suites** (`cli.py`, `replay.py`, `noise/breach_injector.py`, and complete `tests/foundry/` test suite).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | N/A | Architecture follows standard modular design with zero unjustified violations. |

---

