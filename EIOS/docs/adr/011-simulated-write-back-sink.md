# ADR-011: Simulated write-back sink as executor (chaos-failable mock core-systems API)

## Status

Accepted

## Date

2026-10-02

## Context

Approved Action Intents need an executor, and CLAUDE.md invariant 5 forbids any direct-write path. `docs/red_team_findings_v3.md` (finding 10, severity High) records that v2 had no executor for approved actions. `initial_plan.md` section 6.1 defines the sink. This ADR is a backfill of that decision.

## Options considered

- No executor (the v2 gap). Drawback: approved actions go nowhere, so the loop cannot be shown end to end.
- Direct write to a core system. Drawback: violates the no-autonomous-write-back invariant and no such system exists in this engagement.
- Simulated write-back sink: a mock core-systems API that records what would have happened and can fail on demand for chaos tests (chosen). Drawback: it proves the loop and failure handling, not behaviour against a real core system `[ASSUMPTION]` owner: platform lead; verify by the handoff phase review.

## Decision

Use a simulated write-back sink as the only executor of approved Action Intents. It records the would-be effect and can be made to fail on demand.

## Consequences

- Positive: the propose, approve, execute and ledger loop can be demonstrated and chaos-tested without any real write path.
- Negative: results are simulated; real-system integration is out of scope here.
- Follow-ups: add a static check and runtime deny that no direct-write path exists; write chaos tests for sink failure.

## Evidence

**Backfilled** from `initial_plan.md` section 6.1 and `docs/red_team_findings_v3.md` (finding 10). No spike is attached.

## Revisit when

a real core-systems integration is scoped, or sink failure modes prove too coarse for the chaos tests.
