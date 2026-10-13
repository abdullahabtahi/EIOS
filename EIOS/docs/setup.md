# Setup and local checks (FR-003)

Two commands take a clean checkout to a verified working tree. Target: under 30 minutes `[TARGET]`; the latest dry run is in `docs/evidence/sc-002-setup-dry-run.md`.

## Prerequisites

| Tool | Why | Notes |
|---|---|---|
| `uv` | dependency and interpreter management | version in `docs/conventions.md` tooling register `[ASSUMPTION]` |
| Python 3.14 | runtime | `.python-version`; `uv` installs it when missing `[ASSUMPTION]` |
| `make` | the two entry points below | any POSIX make |
| `terraform`, `tflint` | the `iac_plan` gate's full checks | optional locally; the gate reports what it could not run, and CI requires `tflint` |
| `git` | commit reference and history secret scan | optional; without it the commit reference is a content hash and the history scan is skipped with a stated reason |

No cloud account or credential is needed for anything in this document.

## One-command setup

```
make setup        # uv sync: creates .venv from uv.lock
```

## The single local check

```
make check        # uv run python -m tools.gates.local
```

This runs the same fourteen blocking gates, from the same `config/gates.yaml`, as the pull-request pipeline (`.github/workflows/pr.yml`). A test keeps the two in step. Every gate runs even if an earlier one fails; the command exits non-zero when any gate failed.

| Gate | What it checks |
|---|---|
| `lint` | ruff lint and format, plus repository checks (file size, forbidden literals, frozen models, pinned dependencies) |
| `types` | strict mypy |
| `coverage` | pytest with a coverage floor of 80 `[TARGET]` |
| `contract`, `eval_smoke`, `red_line` | the suites registered for that tier in `evals/registry.yaml` |
| `vuln_scan` | dependency advisories (needs network to fetch the advisory database) |
| `secret_scan` | secret-shaped strings in the tree and captured logs |
| `iac_plan` | validity and formatting of infrastructure definitions |
| `infra_policy` | environment isolation, least-privilege service identities, evaluation-truth access (static, no cloud) |
| `open_decision_check` | nothing assumes the outcome of a decision that is still open |
| `label_check` | every figure in the governed docs carries a provenance tag or origin, and cited briefs and spikes exist |
| `adr_check` | decision and spike records are complete and agree with the index in `docs/spikes_and_adrs.md` |

The output ends with the count of quarantined gates (`config/quarantine.yaml`) and a run id.

## Where results go

- `evals/reports/<tool>.json` and `evals/reports/gates/<gate>.log`: per-tool reports and per-gate logs.
- `evals/reports/run-records/<run_id>.json`: the Pipeline Run Record, validated against `schemas/pipeline-run-record.schema.json`.

These are generated and git-ignored.

## Narrower commands

```
make test         # pytest only
make lint         # ruff check and format check
make types        # mypy only
uv run python -m tools.gates.run_gate <gate_id>   # one gate, as CI runs it
```

## Optional switches

| Variable | Effect |
|---|---|
| `EIOS_TEST_NETWORK=1` | runs tests marked `requires_network` (advisory database, fault proof for `vuln_scan`) |
| `EIOS_TEST_EMULATOR=1` | runs tests marked `requires_emulator` |
| `EIOS_TEST_CLOUD=1` | runs tests marked `requires_cloud` |
| `EIOS_REQUIRE_TFLINT=1` | makes a missing `tflint` fail the `iac_plan` gate (set in CI) |

## Conventions

See `docs/conventions.md` for tooling, naming, labelling and the gate and quarantine rules, and `docs/runbooks/branch-protection.md` for the required status checks.
