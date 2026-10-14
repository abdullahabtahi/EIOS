# Spec 032: Engine-backed partner plane and the real decision ledger

**Status**: built; review pending. **Branch**: `feat/engine-partner-compliance`. **Context**: spec 031 (AML plane), `docs/data-strategy.md` (R1), `docs/lighthouse.md`.

## Problem

After spec 031 the AML workstation reads engines, but the partner workstation still reads 20 hand-written partners (one `PartnerChurnItem` per row, a fixed hazard each), the churn and fraud routes return canned payloads that claim to be model output, and the compliance explorer shows three invented ledger rows and a retention-lock claim while the action shelf writes to a real signed ledger nobody reads. The browser also forges shelf cards for retention deals and clawbacks (`DIGEST_SIM_...`, `verified: true`).

## Outcome

Partner and compliance read real sources, and the assistant and the screen read the same objects: a seeded partner world run through the existing churn and fraud engines, and the governance runtime's own ledger, checkpoints and intents.

## Requirements

- **FR-001 World.** `foundry/scenarios/partner_*` builds a deterministic world (240 partners, 70 days of behaviour, messages, commissions, referred-account trades) from `PartnerWorldConfig`. Same config, same bytes. Named partners keep their ids and names.
- **FR-002 Planted truth.** Churn drivers (cashier friction, rival poaching, rebate dispute, dormancy), hard negatives (holiday dips that recover, stable partners who complain or name a rival and stay, churners who never write), a synchronized regional cohort, and opposite-trading pairs under sibling sub-affiliates. A truth table is evaluation only.
- **FR-003 Engines.** `ChurnRadarPipeline` (seasonality filter, discrete-time hazard model, cohort test) at as-of, 14 and 30 days earlier over data cut at each date; `ChurnSignalExplainer`; `TimeBucketedPairDetector`. Quality against the truth is measured on every build and logged.
- **FR-004 Services.** `EnginePartnerService` satisfies `PartnerReadModel` (radar, deals, referral tree, messages, `has_detail`). Every scored partner has detail; the story-partner gating is gone. Root-cause text carries no numbers; every figure has a unit field.
- **FR-005 Honest projections.** A deal's uplift is the drop in the scored hazard when the playbook's signals move, re-scored by the same hazard model. It is labelled a model projection; no refuter p-value or interval is claimed (RL-3). Win rate is absent until outcomes exist.
- **FR-006 Cross-world link.** The partner roster is the AML world's list of referrers; the partner tree shows AML cases among a partner's referrals.
- **FR-007 Compliance.** `ComplianceExplorerService.over_ledger` reads the governance runtime's ledger entries (with actors), signed checkpoints, every intent's sign-offs and a real audit walk. An empty ledger reads as empty; no canned sequence; no retention-lock claim (checkpoints are application-signed anchors).
- **FR-008 Single composition root.** The plane owns the governance runtime; the shelf, the auditor's screen and the assistant share one ledger. Port results carry `data_origin` `engine` for partner and `live` for compliance.
- **FR-009 UI.** Partner rail, radar, cohort banner, inspector, referral network and ontology object read computed data; a missing value shows a dash. Deals, the cohort playbook and clawbacks stage through the hub. The three browser-forged shelf cards on the partner screen are removed; the sample-partner fallbacks in `api-bridge.ts` are removed.

## Measured on the default world `[MEASURED]`

240 partners `[MEASURED]`, of which 51 carry a planted churn driver `[MEASURED]`. Hazard AUC 0.974 `[MEASURED]`; the top 51 by hazard hold 86.3% of them `[MEASURED]`. None of 14 holiday dips scores high risk `[MEASURED]`. The regional cohort is found (31 partners in SEA, binomial p 0.0066) with no false cohort `[MEASURED]`. All 6 planted opposite-trading pairs are found with no false pair `[MEASURED]`. The partner engine builds in about 3 s and the AML engine in about 5 s `[MEASURED]`. The offline agent baseline (scripted model) is identical on both planes: 69 pass, 1 fail (`aml_regulation.t1`, needs retrieval), 3 inconclusive `[MEASURED]`. The 13 percent of planted churners the hazard model misses are partners whose decline is partial or who never write; the model is not tuned to them.

## Out of scope

Executive briefing, forecast and what-if (the 200 ms scenario engine still serves them); operations; retrieval (024); BigQuery (025); a real KMS-locked bucket retention lock.
