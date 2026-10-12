# ADR-012: Warm-start & state strategy for in-memory components (Parquet snapshot; min-instances=1 in prod-like)

## Status

Accepted

## Date

2026-10-02

## Context

Hot state (DuckDB) and the graph (NetworkX) are in memory, and Cloud Run can scale to zero. `docs/red_team_findings_v3.md` (finding 11, severity High) records that this loses state. `initial_plan.md` section 3 (L1 and L2) and risk 5 describe rehydration from a Parquet snapshot and a minimum-instance setting in the prod-like environment. The scale ceiling is the subject of spike S-05. This ADR is a backfill of that decision.

## Options considered

- Run in-memory components on scale-to-zero with no recovery (the v2 design). Drawback: state is lost on every cold start.
- Rehydrate from a Parquet snapshot on cold start, with min-instances=1 in the prod-like environment (chosen). Drawback: a standing instance cost in prod-like and a rehydrate delay on a cold start `[ASSUMPTION]` owner: platform lead; verify by S-05 timings.
- Move graph state to a managed graph database, the production alternative named in ADR-004. Drawback: more infrastructure than the proof of concept needs, per the plan's choice of NetworkX for the POC.

## Decision

Rehydrate in-memory hot state and the graph from a Parquet snapshot on cold start, and set min-instances=1 in the prod-like environment. The scale ceiling is documented; a managed graph database is the named production alternative.

## Consequences

- Positive: state survives restarts and the design stays within a serverless runtime.
- Negative: a standing instance in prod-like; a rehydrate delay on a cold start.
- Follow-ups: spike S-05 measures build and rehydrate time against graph size; ADR-004 records the graph engine choice.

## Evidence

**Backfilled** from `initial_plan.md` section 3 (L1, L2) and section 11 risk 5, and `docs/red_team_findings_v3.md` (finding 11). Related spike: S-05 (`S-05-graph-scale-ceiling.md`).

## Revisit when

spike S-05 shows the snapshot rehydrate time or the graph ceiling is unacceptable, or ADR-004 selects a managed graph store.
