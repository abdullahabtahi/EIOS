# Contract: Gate Hook Registry

**Feature**: F00 | **Requirements**: FR-004..FR-009, FR-012 | **Constitution**: VI, VIII | **File**: `evals/registry.yaml`

Design-time contract for how later features plug evaluation suites into the pipeline without editing workflows.

## Registry entry

```yaml
- id: <unique suite id>
  tier: contract | eval_smoke | red_line | validation | sealed
  command: <command the runner executes>
  owner_feature: F<NN>
  report: evals/reports/<id>.<ext>
```

| Field | Rule |
|---|---|
| id | unique, kebab-case |
| tier | one of the five tiers |
| command | non-empty; resolved relative to the repository root |
| owner_feature | matches `^F[0-9]{2}$` |
| report | path under `evals/reports/` |

## Tiers and where they run

| Tier | `pr` | `promote-stage` | `promote-prod-like` | `release-candidate` |
|---|---|---|---|---|
| contract | yes | yes | yes | yes |
| eval_smoke | yes | yes | yes | yes |
| red_line | yes | yes | yes | yes |
| validation | no | yes | yes | yes |
| sealed | never | never | never | yes |

Sealed suites run only under the release-candidate workflow identity. Other identities have no read access to sealed data or ground-truth labels (Constitution VI).

## Runner behaviour

| Situation | Result |
|---|---|
| Registry empty | run prints "no suites registered" and passes |
| Registered suite exits non-zero | gate fails; run state `failed` |
| Registered suite command missing or not executable | gate fails, not skipped |
| Report file not produced | gate fails |
| Duplicate id, unknown tier, malformed entry | registry validation fails before any suite runs |
| Suite skipped | allowed only as `skipped_with_reason` with a non-empty reason recorded on the run |

Every result is written to the Pipeline Run Record ([pipeline-run-record.schema.json](./pipeline-run-record.schema.json)) with a `report_ref`.

## Red-Line hook

The Red-Line tier is a named hook in the `pr` and promotion workflows from day one. In F00 it contains no suites; RL-1..RL-7 arrive with the features that own them. The hook must exist and run so that adding a suite later needs only a registry entry.

## Tests owned by F00

- Empty registry passes with the expected message.
- A registered failing suite fails the run.
- A registered suite with a missing command fails the run.
- A malformed registry fails before execution.
- A sealed suite is not executed by the `pr` workflow.
