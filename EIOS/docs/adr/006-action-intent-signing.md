# ADR-006: Action Intent signing (Cloud KMS ECDSA P-256, nonce, expiry, rotation)

## Status

Accepted

## Date

2026-10-02

## Context

Every mutation is an Action Intent that a human approves and a simulated sink executes (CLAUDE.md invariant 5). The earlier plan (v2) signed intents with HMAC-SHA256. `docs/red_team_findings_v3.md` (finding 7, severity High) records that this was symmetric, had no rotation and no replay control. `initial_plan.md` section 6.1 states the replacement. This ADR is a backfill of that decision.

## Options considered

- HMAC-SHA256 tokens (the v2 design). Drawback: symmetric key, no non-repudiation, no rotation and no replay control, per the red-team finding.
- Cloud KMS asymmetric signature, ECDSA P-256, with nonce, expiry, idempotency record and key-version rotation (chosen). Drawback: adds a KMS dependency and a per-signature cost; the real cost is to be recorded by spike S-06 `[SPIKE]` S-06.
- Self-managed signing keys held in the application secret store. Drawback: rotation, access control and audit would be built and operated by the team `[ASSUMPTION]` owner: security lead; verify by S-06 review.

## Decision

Sign Action Intents with a Cloud KMS asymmetric key (ECDSA P-256). Each intent carries a nonce, issue time and expiry; the nonce and idempotency key are stored in a transactional store (Firestore) so a token is single-use; rotation uses KMS key versions and the verifier checks the key id.

## Consequences

- Positive: non-repudiation, replay protection and rotation that HMAC could not provide.
- Negative: a KMS dependency in every environment that signs, with a cost that is not yet measured; the expiry length is an `[ASSUMPTION]` in the source plan, owner: security lead, verify by S-06.
- Follow-ups: run spike S-06 for verification only (sign and verify with rotation, write-only IAM, real cost); the decision stands unless S-06 finds a blocker.

## Evidence

**Backfilled** from `docs/red_team_findings_v3.md` (finding 7) and `initial_plan.md` section 6.1. S-06 pending verification: see `S-06-kms-signing-and-ledger.md`.

## Revisit when

spike S-06 shows signing cost or latency is unacceptable, or a key-management requirement appears that KMS versions cannot meet.
