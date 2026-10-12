# SC-008 and SC-011: decision records, readiness and open-decision check

**Date**: 2026-10-02. **Tools**: `uv run python -m tools.adr_check` (the thirteenth blocking PR gate, `adr_check` in `config/gates.yaml`), `uv run python -m tools.readiness <feature>`, `uv run python -m tools.open_decision_check`.

## What was run

| Check | Where | Result |
|---|---|---|
| Real records agree with the index | `tests/integration/test_real_decision_records.py` | 0 findings; every `Accepted` ADR has a backfilled record; all 7 spikes have an open record |
| Each mismatch class fails with its own rule id | `tests/unit/tools/adr_check/` over `tests/fixtures/decisions/adr_check/` | missing file, missing index entry, status mismatch, duplicate number, one-way supersession, missing field, no evidence, fewer than two options, closed spike without a linked ADR, closed spike linking an `Open` ADR |
| Templates parse and fail when unfilled | `tests/unit/tools/records/test_templates.py` | pass |
| Readiness blocked, then ready | `tests/unit/tools/readiness/`, `tests/unit/tools/decisions/test_readiness_cli.py` | blocked lists every unmet spike, ADR and feature with its state (exit 1); closing the spike with an `Accepted` ADR gives exit 0 on the next run; a malformed declaration is exit 2 |
| Open decisions stay open | `tests/unit/tools/open_decision_check/` | ADR-002, 003, 009 and 014 report open on the clean tree; each rule kind flags its planted violation |
| Faulty-change proof | `tests/integration/test_faulty_changes.py` with `tests/fixtures/faulty_changes/adr_check/` | gate fails on an `Accepted` index row with no record file and passes on the clean skeleton |

## Backfilled records

ADR-001, 006, 007, 010, 011, 012, 013 and 015 are `Accepted` in the index and now have records under `docs/adr/`. Each cites a planning document as evidence and says it is backfilled, because the decision predates the records. Drawbacks the sources did not state are tagged `[ASSUMPTION]` with an owner and a verify-by note. ADR-006 and 007 note that S-06 is pending verification. No status in the index was changed.

## Spike records

S-01 to S-07 are all `open`: each has a question, time box and owner, and no result. None is closed, so every feature that depends on one stays blocked until the spike runs.

## Limits

- The agreement rule compares number, title and status; it does not judge whether the text of a decision is sound.
- Backfilled evidence is a design-document reference, not an experiment; it cannot be machine-verified.
- Spike owners are roles tagged `[ASSUMPTION]`, not named people.
- `open_decision_check` is pattern and config driven; a decision assumed through a candidate name absent from the config is not caught.
- `docs/feature_register.yaml` is maintained by hand; `complete` is not derived from task state.
