# Runbook: branch protection and gate bypass (FR-005, FR-012)

**Audience**: repository administrators. **Source of truth for gates**: `config/gates.yaml`.

## Required status checks

Configure the protected branch so that every one of these checks is required and must be up to date before merge. The check names are the gate ids; `.github/workflows/pr.yml` runs each gate as its own step so each appears separately.

| Required check (gate id) | What it blocks |
|---|---|
| `lint` | style, formatting, repository hygiene checks |
| `types` | strict type errors |
| `coverage` | coverage below 80% `[TARGET]` |
| `contract` | broken data-contract suites registered in `evals/registry.yaml` |
| `eval_smoke` | failing smoke evaluations |
| `red_line` | failing Red-Line suites (hook is live; no suites are registered in F00) |
| `vuln_scan` | dependencies with published advisories at or above the configured severity `[TARGET]` |
| `secret_scan` | secret-shaped strings in the tree or captured logs |
| `iac_plan` | invalid or unformatted infrastructure definitions |
| `infra_policy` | shared or over-privileged service identities, shared environment state, ungranted evaluation-truth access |
| `open_decision_check` | code or configuration that assumes the outcome of a still-open decision (ADR) |
| `label_check` | an unlabelled or mis-evidenced figure, a missing brief or spike reference, a forbidden literal in the governed docs |
| `adr_check` | a decision or spike record with a missing field, or disagreeing with the index (missing file, status mismatch, one-way supersession) |

The list must equal the `pr`-stage ids in `config/gates.yaml`. When a later feature adds a gate row, add the new id here in the same change. `tests/unit/tools/gates/test_local_parity.py` keeps the workflow and the config in step; this table is kept in step by review.

Other branch rules:

- Require pull requests before merging; no direct pushes to the protected branch, including for administrators.
- Dismiss stale approvals when new commits arrive.
- Require linear history `[ASSUMPTION]`.

## The only permitted bypass

A gate may be skipped only as a `skipped_with_reason` entry on the Pipeline Run Record, with a non-empty reason, naming the person accountable. There is no other bypass: no admin override of required checks, no `--no-verify`, no editing a gate to always pass.

## Quarantine procedure (FR-012)

Use quarantine only for a gate that is itself broken (for example a flaky third-party advisory feed), never to merge a real failure.

1. Add an entry to `config/quarantine.yaml` with `gate_id`, `owner` (a named person), `expires` (an ISO date, at most 14 days out `[TARGET]`) and `reason`.
2. The change goes through normal review; the reviewer confirms the gate is broken, not the code.
3. While the entry is live, the gate is recorded as `skipped_with_reason` citing the quarantine, and every run summary prints the number of quarantined gates.
4. When `expires` passes, the run fails until the gate is repaired and the entry is removed or a new reviewed entry is added.
5. The owner removes the entry in the same change that repairs the gate.

A run with any quarantined gate is visible on the Pipeline Run Record; review the count at least weekly `[TARGET]`.

## Checking the configuration

Compare the repository's required status checks against `config/gates.yaml`. Record the date checked in `docs/evidence/` when the protection rules change.

## Plan checks and the protected environment (T093, FR-007)

- `plan-dev`, `plan-stage` and `plan-prod-like` (the `plan` job in `pr.yml`) show each environment's infrastructure change with a read-only federated identity. They never change anything, and are skipped for pull requests from forks. Require them once the repository variables `EIOS_WORKLOAD_IDENTITY_PROVIDER`, `EIOS_PLAN_SERVICE_ACCOUNT` and `EIOS_STATE_BUCKET` exist; the identity pool is created by `infra/bootstrap`.
- Create the GitHub environment `prod-like` with required reviewers. `promote-prod-like.yml` binds every job to it; the approver recorded on the run is read from the platform's approvals record, never typed in.
