# ADR-013: Streaming vs batch separation and shared hot state

## Status

Accepted

## Date

2026-10-02

## Context

Ingestion (contract validation, then hot state) must stay responsive while batch work (feature materialisation, training, SCM fitting) runs. `initial_plan.md` section 3.1 invariant 3 states: batch and streaming are decoupled, and the streaming path never blocks on batch. This ADR is a backfill of that decision.

## Options considered

- One pipeline that runs streaming and batch work together. Drawback: a slow batch job (training, SCM fitting) can stall ingestion and hot-state freshness `[ASSUMPTION]` owner: architecture lead; verify by the streaming-path soak test.
- Decoupled streaming and batch paths that meet at shared hot state (chosen). Drawback: two paths to build, test and keep consistent through the shared state `[ASSUMPTION]` owner: architecture lead; verify by integration tests across both paths.

## Decision

Keep the streaming path (ingest, contract, hot state) separate from the batch path, and let them share hot state. The streaming path never blocks on batch work.

## Consequences

- Positive: ingestion stays fresh while heavy batch jobs run; the invariant is testable.
- Negative: two paths and a shared-state contract to maintain.
- Follow-ups: write the invariant 3 test; define what each path may read from and write to the shared state.

## Evidence

**Backfilled** from `initial_plan.md` section 3.1 (invariant 3) and the ADR index in `docs/spikes_and_adrs.md`. No spike is attached.

## Revisit when

a requirement needs the streaming path to wait on a batch result, or shared hot state becomes a contention point.
