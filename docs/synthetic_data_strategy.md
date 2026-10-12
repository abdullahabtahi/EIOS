# Synthetic Enterprise Data Foundry (Layer 0) — v3

Companion to `initial_plan.md` §3 (L0) and §8 (slices). Supersedes v2 (archived context in `docs/red_team_findings_v3.md`). Tags per `initial_plan.md` §0.2: `[BRIEF]` `[ASSUMPTION]` `[ILLUSTRATIVE]` `[TARGET]` `[SPIKE]`.

---

## 1. Why this exists

In a real forward-deployed engagement the client's data is unavailable or unusable until trust is built. The Pilot pattern is to stand up a realistic stand-in, prove the loop end-to-end, then swap in real feeds. L0 is that stand-in: seeded generators that write to the **same Pub/Sub topics and contracts** a real feed would use, so nothing above L1 knows the data is synthetic.

## 2. Provenance rule

Every figure shown in the cockpit, an eval report or the case study must trace to one of:

1. a **brief citation** (`docs/brief/*`), tagged `[BRIEF]`;
2. a **generator run** at a stated seed + git SHA + spec hash + dataset hash;
3. an **eval report** (`evals/reports/`).

Anything else is `[ASSUMPTION]` or `[ILLUSTRATIVE]` and must be labelled as such wherever it appears. No unlabelled invented numbers.

## 3. Design principles

1. **Seeded and reproducible.** Every run emits a manifest `{seed, git_sha, spec_hash, dataset_hash, generator_versions}`. Same manifest ⇒ byte-identical Parquet.
2. **Pattern-first.** Target patterns (rings, churn cohorts, causal chain, round-trip laundering) are declared in YAML specs and embedded by construction; specs are versioned.
3. **Background noise plus hard negatives.** Planted positives sit inside realistic benign behaviour, including legitimate cases that *look* suspicious.
4. **Shared entity IDs.** One entity universe across generators (ClientAccount, Partner, Device, IP, PaymentMethod, Competitor) so cross-domain joins and causal chains are real. IDs are generated, never hand-typed.
5. **Contract-checked at generation time.** Generators validate against the L1 Pydantic contracts before publishing; a generator that violates a contract fails its own CI.
6. **Grounded where a brief gives numbers; `[ILLUSTRATIVE]` elsewhere.**

## 4. Anti-circularity controls (ADR-015)

The main risk (R1): models "discover" what the generator planted. Controls:

| Control | Rule |
|---|---|
| Seed splits | `dev` (free use), `validation` (model selection, CI), `sealed` (generated from specs the model authors have not seen; evaluated by CI on release candidates only) |
| Hard negatives | Legitimate high-volume traders; hedgers and introducing-broker portfolios (opposite positions, legitimate); seasonal partner dips; shared-context IPs (offices, campuses, mobile carrier NAT) |
| Label noise | `[ASSUMPTION]` 3–8% of analyst labels flipped at random and by ambiguity |
| Placebo edges | Causal-truth generator plants edges with true effect = 0 that the causal gate must reject |
| Sealed typologies | ≥ 2 fraud/churn typologies never described in model-author docs; used to test novelty discovery |
| Distribution shift | Sealed seeds vary volume, seasonality and noise level relative to dev |
| Eval-only ground truth | Truth labels written to a separate bucket readable only by the eval harness and CI service account; never visible to agents, models at inference, or the cockpit |

## 5. Generators

| Generator | Produces | Feeds | Notes |
|---|---|---|---|
| `gen_client` | ClientAccount, funnel, devices, IPs, payment methods, sessions | `client_360`, `client_funnel`, `device_network_graph` | Background population, segments, KYC lifecycle |
| `gen_aml` | Deposits, withdrawals, trades, alerts, analyst decisions | `transactions_aml`, `trading_activity`, `compliance_cases` | Module A patterns and hard negatives |
| `gen_partner` | Partners, referral trees, commissions, engagement signals, comms | `partner_360`, `partner_referral_tree`, `commission_ledger`, `partner_engagement_signals`, `partner_comms` | Modules B and C patterns |
| `gen_financial` | Revenue, cost, margin, LTV cohorts | `financial_pnl` | Driven by client and partner behaviour so causal links are genuine |
| `gen_competitive` | Competitor payout/spread/promo events | `competitor_benchmarks` | Competitor names are generic aliases, not real brands |
| `gen_operational` | Latency, incidents, disputes | `platform_operations` | Includes benign noise and one planted operational shock |
| `gen_causal_truth` | Structural equations + true edge effects (incl. placebo) | eval-only bucket | Single source of truth for Synthesis evaluation |

Ground truth for all generators is written to the eval-only bucket, never to Pub/Sub.

## 6. Module B ring spec (source: `docs/brief/fraud`)

```yaml
scenario: partner_mirror_trading_ring
seed: 42                       # [BRIEF] seed value is ours; structure below marked per field
partners: 7                    # [BRIEF]
referral_layers: 3             # [BRIEF]
sub_affiliates: 23             # [BRIEF]
clients: 184                   # [BRIEF]
opposite_trading_pairs: 23     # [BRIEF]
timing_correlation: 0.89       # [BRIEF]
instruments: generated         # [ILLUSTRATIVE] chosen by generator, not hand-typed
bonus_abuse_share: 0.35        # [ILLUSTRATIVE]
hard_negatives:                # [ILLUSTRATIVE]
  - legitimate_hedgers: 40
  - ib_portfolios_opposite_positions: 12
  - genuine_high_volume_referrers: 15
ids: generated                 # never hand-typed
ground_truth_bucket: eval-only
```

## 7. Module C churn spec (source: `docs/brief/churn`)

```yaml
scenario: partner_churn_population
seed: 7
partners: 5000                 # [BRIEF]
hazard_process: discrete_time_logistic   # [ILLUSTRATIVE]
signal_families: [login_decay, referral_velocity, conversion, ticket_sentiment, competitor_language]  # per brief
decay_lead_days: 21-60         # [ILLUSTRATIVE]
seasonal_dip_hard_negatives:   # [ILLUSTRATIVE]
  share_of_partners: 0.08
  recover_after_days: 30
cohort_event:                  # [ILLUSTRATIVE]
  partners: 8
  region: generated
  lag_days: 14
comms_poaching_share: 0.04     # [ILLUSTRATIVE]
sarcasm_negation_hard_cases: true
ground_truth_bucket: eval-only
```

## 8. Module A design (source: `docs/brief/monitoring.md`)

Anchors from the brief (`[BRIEF]`): ~2,000 alerts per week; ~95% false positives; round-trip pattern `$500 → 10 min → $0.01 → withdraw`; activity within 72 hours of KYC approval; a network of 47 linked accounts.

Everything else is `[ILLUSTRATIVE]`:

- Ring sizes and topology beyond the 47-account anchor, plus additional smaller rings.
- Background alert stream calibrated so that ~95% are benign by construction.
- Hard negatives: legitimate high-volume traders, expatriate families sharing a device/IP, business users with several payment methods.
- **Hub-suppression stress test:** a synthetic office/campus/carrier-NAT IP with hundreds of unrelated accounts. Naive shared-IP components will merge them; the ring detector must not (metric: hub false-merge rate, see `docs/models_and_evals.md` §2).
- Sealed typology: at least one AML pattern not described in the brief.

## 9. Where this plugs in

- **L1:** generators publish to the production Pub/Sub topics; contract validation, DLQ and ER are exercised for real, including seeded contract-breach and duplicate-identity injections (S-07).
- **L2:** entity universe and metric registry populated from L1 output only.
- **L3 evals:** eval harness reads ground truth from the eval-only bucket and scores agents/models on `dev`/`validation`/`sealed` seeds.
- **L5 flywheel:** forward-simulation of 30/60/90-day outcomes for approved actions, so the decision-outcome ledger can recalibrate causal-edge weights without real customers.

## 10. Spec-kit decomposition (`F01-synthetic-foundry`)

1. Manifest and seed-split framework.
2. Shared entity universe (`gen_client`).
3. Per-domain generators, in order: partner → aml → financial → competitive → operational.
4. `gen_causal_truth` with placebo edges.
5. Hard-negative and label-noise injectors.
6. Contract-at-generation validation.
7. Eval-only bucket and access policy.
8. Sealed-seed generation pipeline (CI-only).
9. Determinism tests: same manifest ⇒ same dataset hash.
