# Contract: Decision and Spike Records

**Feature**: F00 | **Requirements**: FR-032..FR-035 | **Constitution**: V, VI | **Tools**: `tools/adr_check`, `tools/readiness`, `tools/open_decision_check`

Design-time contract for the ADR and spike workflow. Source formats follow `docs/spikes_and_adrs.md`.

## ADR file

Location: `docs/adr/NNN-title.md` (three-digit number, kebab-case title).

| Field | Rule |
|---|---|
| Title | `ADR-NNN: <text>`; number matches the filename |
| Status | one of `Proposed`, `Accepted`, `Superseded by ADR-XXX` (`Open` appears only in the index for undecided items and has no file until proposed) |
| Date | ISO `YYYY-MM-DD` |
| Context | non-empty |
| Options considered | at least two |
| Decision | non-empty when status is `Accepted` or `Superseded` |
| Consequences | non-empty |
| Evidence | links to a spike, eval report or brief citation; required when `Accepted`. A record backfilled from a decision taken before F00 may instead cite a design document under `docs/` or `initial_plan.md`, and must say it is backfilled |
| Revisit when | non-empty trigger |

State transitions: `Open → Proposed → Accepted → Superseded`. A superseding ADR must name the ADR it replaces, and the replaced ADR must name its successor.

## Index agreement

The index in `docs/spikes_and_adrs.md` and the files in `docs/adr/` must agree on number, title and status. `Proposed` and `Open` entries may have no file; `Accepted` and `Superseded` entries require one. `adr_check` fails on: index entry with no file where status is `Accepted` or `Superseded`, file with no index entry, status mismatch, duplicate numbers, and a broken supersession chain.

## Spike record

| Field | Rule |
|---|---|
| Id | `S-NN` |
| Question | non-empty |
| Time box | stated `[TARGET]` |
| Owner | non-empty |
| State | `open` or `closed` |
| Method, Data, Result, Decision, Date, Outcome | required when closed; an open spike needs only Question, Time box and Owner |
| Linked ADR | required when closed; must exist in the index and not be `Open` |

A spike cannot close without a linked ADR.

## Feature dependency declaration

Each feature declares its dependencies in `specs/<feature-dir>/dependencies.yaml`, conforming to [feature-dependencies.schema.json](./feature-dependencies.schema.json) (copied to `schemas/`). `docs/feature_register.yaml` lists every feature id (F00 to F15) with a boolean `complete` flag.

## Readiness rule (`tools/readiness <feature>`)

Ready only when all hold:

1. every `depends_on_spikes` entry is `closed`;
2. every `depends_on_adrs` entry is `Accepted`;
3. every `depends_on_features` entry is marked complete in the feature register.

Otherwise the tool exits non-zero and lists each unmet dependency with its current state.

## Open-decision check (`tools/open_decision_check`)

ADR-002 (LLM), ADR-003 (metric engine), ADR-009 (frontend) and ADR-014 (API surface) stay open through F00. The check scans code, config and infrastructure for choices bound to those decisions (vendor SDK imports outside `providers/`, model identifiers, metric-engine or frontend framework manifests, API framework routes) and fails when any is found while the ADR is not `Accepted`. Once an ADR is `Accepted` the corresponding rule is lifted by configuration in `config/open_decisions.yaml`, not by editing the tool.

## Tests owned by F00

- Fixtures for each `adr_check` failure class.
- A spike closing without an ADR is rejected.
- `readiness` blocks on each of the three dependency kinds and passes when all are met.
- `open_decision_check` fails on a planted vendor SDK import and passes on the stub provider only.
