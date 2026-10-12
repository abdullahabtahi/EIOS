# ADR-007: Ledger tamper-evidence (write-only IAM, hash chain, retention-locked anchors)

## Status

Accepted

## Date

2026-10-02

## Context

The Decision Ledger must be trustworthy for audit. The v2 plan called the BigQuery ledger immutable. `docs/red_team_findings_v3.md` (finding 8, severity High) records that BigQuery is not immutable. `initial_plan.md` section 6.2 states the controls. This ADR is a backfill of that decision.

## Options considered

- Treat BigQuery as immutable (the v2 claim). Drawback: false; rows can be altered by anyone with write access, so tampering would go unseen.
- BigQuery with write-only IAM for the service account (no update or delete), hash-chained rows, periodic chain-head anchors to a bucket with retention lock, and a verifier job that alerts on a chain break (chosen). Drawback: more moving parts to build and operate, and the BigQuery constraints are not yet exercised `[SPIKE]` S-06.
- Firestore-backed append log plus anchor, the fallback named in spike S-06. Drawback: a different store from the analytics tables, so reporting needs a copy `[ASSUMPTION]` owner: data platform lead; verify by S-06 result.

## Decision

Keep the ledger in BigQuery and make tampering evident: append-only through a write-only IAM role, hash-chained rows (previous-hash field), chain-head anchors written periodically to a retention-locked GCS bucket, and a verifier job that alerts on a chain break, exercised by a tamper drill.

## Consequences

- Positive: tampering becomes detectable rather than assumed impossible.
- Negative: the verifier, anchor job and drill are extra components to run and test.
- Follow-ups: spike S-06 verifies the controls (hash chain, retention-locked anchor, tamper drill); if BigQuery constraints bite, switch to the Firestore-backed fallback.

## Evidence

**Backfilled** from `docs/red_team_findings_v3.md` (finding 8) and `initial_plan.md` section 6.2. S-06 pending verification: see `S-06-kms-signing-and-ledger.md`.

## Revisit when

spike S-06 shows the BigQuery constraints defeat the controls, or the tamper drill fails to detect a modification.
