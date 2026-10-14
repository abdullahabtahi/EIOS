# Spec 031: Engine-backed AML data plane

**Status**: built; review pending. **Branch**: `feat/engine-backed-aml`. **Context**: `docs/data-strategy.md` (R1), `docs/agent-architecture.md` section 2, `docs/lighthouse.md` (M1, M6).

## Problem

The AML workstation and the assistant read hand-written payloads: 3 alerts, one dossier (`CR84920`), `data_origin: fixture`. The real detectors (`aml/`) are tested but never see behavioural data (S-DATA-1: foundry output has one transaction per client, so the pipeline finds 0 round-trips and 0 alerts). The browser also builds per-alert dossiers from client-side fixtures, and the assistant builds its own `ReadModels`, so screen and chat share no objects.

## Outcome

One AML data plane under the screen and the assistant: a seeded world of clients with realistic behaviour and planted, labelled typologies; the existing detectors and triage scorer run over it; any alert opens a computed dossier, graph, timeline and SAR draft; the assistant answers about any alert and agrees with the card.

## Requirements

- **FR-001 World.** `foundry/scenarios` builds a deterministic world from a config (seed, clients, window, as-of). Same config, same bytes. No wall clock.
- **FR-002 Typologies and truth.** The world plants micro-P&L wash round-trips, income-discrepancy structuring and mule rings, plus hard negatives (CGNAT hubs, households, scalpers, large legitimate depositors). A truth table records every planted client and ring.
- **FR-003 Story continuity.** `CR84920` (income $500, 16 deposits of $500 in USDT, ring of 23, pending withdrawal $7,800 two hours after the last deposit), `CR91204` (round-trip inside 12 minutes) and `CR73491` (device ring of 8) exist with those facts, so existing golden cases hold.
- **FR-004 Detection.** Raw alerts come from the real detectors with features computed from data (peer z-score from cohort baselines, hours since KYC, turnover ratio, market risk, ring size). Hub suppression uses the RL-4 degree of 100. No constant features.
- **FR-005 Triage.** About 2,000 raw alerts compress to a ranked queue of at most 50 cases through `AlertTriageScorer`; one case per client.
- **FR-006 Measured quality.** Precision and recall against the truth table are computed at build and reported `[MEASURED]` (top-50 precision, recall of planted accounts, hub false-merge count).
- **FR-007 Services.** `EngineAMLService` has the public methods of `AMLWorkstationService` and the same contract dicts; plus a per-entity case payload. Contract validation passes.
- **FR-008 Single composition root.** The cockpit server builds one `ReadModels` from the selected plane and hands it to the workstation routes, the tool port and the assistant gateway.
- **FR-009 Plane switch.** `EIOS_DATA_PLANE=engine|fixture`; `fixture` under `EIOS_ENVIRONMENT=test`, `engine` otherwise. The build is cached on disk keyed by config and code version; a cold build over 3,000 clients finishes in under 20 s `[TARGET]`.
- **FR-010 Origin.** Port results from the engine plane carry `data_origin: engine`; the wire contract and proxies pass it through; the header reads `Pipeline: Engine`; the `DEMO` badge is removed.
- **FR-011 UI.** Selecting an alert fetches that entity's case from the backend (dossier, graph, SAR); the triage rail lists the ranked cases with search; the chat answers about any case and its figures agree with the card.
- **FR-012 Honesty.** A causal flag shows only if the placebo refuter passes (RL-3); otherwise "Correlation Only". An unknown id is `NOT_FOUND`.

## Success criteria

- SC-001 The offline agent baseline (`--runtime adk`) is not worse than before on the 22 golden cases.
- SC-002 `make check` green; `npx tsc --noEmit` 0 errors; web tests pass.
- SC-003 Twelve different alerts opened in the UI each show a distinct, internally consistent dossier; the assistant's figures equal the card's (extended FR-026 parity test).
- SC-004 Top-50 precision and planted-account recall are printed in the build log and stored with the snapshot `[MEASURED]`.

## Out of scope

Partner, executive, compliance wiring (spec 032); retrieval (024); BigQuery (025); ambient dossiers (029).

## Measured on the default world `[MEASURED]`

6,000 accounts, 30 days, seed 20261014: 1,684 raw alerts `[MEASURED]` became 1,130 cases `[MEASURED]` (a ring is one case). Of 35 cases containing planted accounts `[MEASURED]`, 33 sit in the top 50 `[MEASURED]` (precision at 50 is 0.66 because only 35 planted cases exist to fill 50 slots; 98% of planted accounts are covered `[MEASURED]`). Every planted ring was recovered whole and the largest cluster is the planted 23, so no hub merged the world `[MEASURED]`. The engine builds in about 5 s `[MEASURED]`. Offline agent baseline (scripted model) is identical on both planes: 69 pass, 1 fail (`aml_regulation.t1`, needs the retrieval tool of spec 024), 3 inconclusive `[MEASURED]`. The two planted wash accounts missed by the top 50 are a measured weakness of the existing triage scorer, not tuned away.

## What it does not do yet

SAR statutory citations are empty until retrieval (spec 024); partner, executive, compliance and operations are still fixtures (spec 032); the engine build is not cached on disk (about 5 s at start).
