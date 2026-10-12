# ADR-015: Synthetic-data split policy (dev/validation/sealed) & anti-circularity controls

## Status

Accepted

## Date

2026-10-02

## Context

The main risk (R1) is that models discover what the generator planted. `docs/synthetic_data_strategy.md` section 4 sets the controls and names this ADR. `docs/red_team_findings_v3.md` (finding 3, Critical) records synthetic circularity. This ADR is a backfill of that decision.

## Options considered

- One shared synthetic dataset used for development, selection and evaluation. Drawback: results reflect what the generator planted, so the evaluation is circular.
- Seed splits with anti-circularity controls: dev for free use, validation for model selection and CI, sealed for release-candidate evaluation by CI only; with hard negatives, label noise, placebo edges, sealed typologies, distribution shift and eval-only ground truth (chosen). Drawback: more generator work and a CI-only sealed pipeline `[ASSUMPTION]` owner: data science lead; verify by the sealed-seed generation pipeline build.

## Decision

Adopt the dev, validation and sealed seed splits and the anti-circularity controls in `docs/synthetic_data_strategy.md` section 4. Sealed seeds are generated from specs the model authors have not seen and evaluated only by CI on release candidates. Ground-truth labels live in an eval-only bucket that agents, models at inference and the cockpit cannot read.

## Consequences

- Positive: evaluation results can be reported as deltas on holdouts the model developer never saw.
- Negative: generator complexity and a CI-only sealed pipeline; label-noise rates are an `[ASSUMPTION]` in the source, owner: data science lead, verify by the first evaluation run.
- Follow-ups: build the manifest and seed-split framework and the sealed-seed pipeline; add the eval-only bucket permissions.

## Evidence

**Backfilled** from `docs/synthetic_data_strategy.md` section 4 and `docs/red_team_findings_v3.md` (finding 3). No spike is attached.

## Revisit when

a sealed seed is exposed to model authors, or evaluation shows the controls do not separate planted from discovered patterns.
