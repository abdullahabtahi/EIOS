# Contract: Cost Model and Budget Alerts

**Feature**: F00 | **Requirements**: FR-038, FR-011, FR-022 | **Constitution**: V, VIII | **Tool**: `tools/cost_check`

Design-time contract for the cost model file and its checker. All figures are placeholders until verified; none is invented as fact.

## File

`docs/cost_model.csv`, one row per cost driver.

| Column | Rule |
|---|---|
| driver | unique, non-empty (e.g. model tokens, compute, storage, scanning) |
| unit | non-empty billing unit |
| quantity | number ≥ 0, or blank when not yet estimated |
| unit_price | number ≥ 0, or blank when not verified |
| price_source | non-empty when unit_price is set (link or document reference) |
| price_verified_on | ISO date; required when unit_price is set |
| tag | one of the five provenance tags; required on every row |

## Checker rules

| Situation | Result |
|---|---|
| Row has unit_price but no price_source or price_verified_on | fail |
| Row tag missing or not one of the five | fail |
| Row tagged `[SPIKE]` without a spike id in price_source | fail |
| price_verified_on older than the staleness threshold `[TARGET]` | warning, listed in the report |
| Duplicate driver | fail |
| Blank unit_price | allowed; the row is reported as "unverified" and excluded from totals |

Totals are computed by the tool from rows; nothing in the file is a hand-typed total.

## Model-cost linkage

Model token prices in the gateway configuration ([llm-gateway-config.schema.json](./llm-gateway-config.schema.json)) and the corresponding driver rows here must not disagree: `cost_check` compares them and fails on a mismatch.

## Budget alerts

Each deployed environment has a budget with alert thresholds at 50%, 80% and 100% `[TARGET]`. Alerts go to a notification channel declared in infrastructure code; the threshold values live in configuration, not in code. Reconciliation against the actual bill is recorded as a status on each row once a bill exists.

## Tests owned by F00

- Fixture per failure row.
- Clean file passes and prints totals for verified rows only.
- Mismatch between gateway prices and cost rows fails.
- Infrastructure plan for each environment contains the three budget thresholds.
