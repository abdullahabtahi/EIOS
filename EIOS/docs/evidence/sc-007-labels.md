# SC-007: provenance label check

**Date**: 2026-10-02. **Tool**: `uv run python -m tools.label_check`, the twelfth blocking PR gate (`label_check` in `config/gates.yaml`). **Result**: seeded recall is 11 of 11 and the clean fixture and governed F00 docs report 0 findings.

## What was run

| Check | Where | Result |
|---|---|---|
| Seeded recall | `tests/integration/test_label_check_seeded_recall.py` over `tests/fixtures/label_check/seeded/` | 11 of 11 seeded violations found, nothing else reported |
| Clean tree | same test, `tests/fixtures/label_check/clean/` | 0 findings |
| F00 governed docs | `tests/integration/test_label_check_f00_docs.py` | 0 findings |
| Faulty-change proof | `tests/integration/test_faulty_changes.py` with `tests/fixtures/faulty_changes/label_check/` | gate fails on the overlay (unlabelled percentage) and passes on the clean skeleton |
| Unit rules | `tests/unit/tools/label_check/` | all pass |

The seeded set covers 8 rule ids: `label.spike-reference` (3), `label.forbidden-literal` (2), and one each of `label.unlabelled-claim`, `label.brief-citation`, `label.multiple-tags`, `label.unknown-tag`, `label.origin-incomplete`, `label.origin-path`. A recall of 1.0 on 11 seeded cases is a statement about this fixture, not a general detection rate.

## Governed scope

The repository run scans 6 files (`scanned_count` in `evals/reports/label_check.json`) and excludes 6 paths, including the prototype tree. Spike states are resolved from `docs/spikes_and_adrs.md` until T173 adds the spike records under `docs/adr/`.

## Allowlist

`config/label_allowlist.yaml` is empty. An entry with a blank reason is rejected as a configuration error (exit 2), so every exception must say why.

## Limits

- Only brief citations, spike ids and origin references are machine-checked. Evidence behind `[ASSUMPTION]` and `[TARGET]` tags is documented in `docs/conventions.md` but not verified.
- A cited brief section is checked for presence of a reference, not for whether the brief supports the figure.
- Claim detection is pattern-based (percentage, currency, count, duration, ratio); prose figures outside these shapes are not caught.
