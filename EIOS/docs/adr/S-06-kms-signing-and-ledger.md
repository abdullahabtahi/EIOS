# S-06: KMS signing, ledger tamper-evidence and real cost

## Id

S-06

## Question

Do KMS signing and ledger tamper-evidence work as designed, and what is the real cost?

## Time box

At most 1 day [TARGET] metric: spike_duration, reported in the Result section when the spike runs.

## Owner

Platform lead [ASSUMPTION] owner: engagement lead; verify by S0 kickoff.

## State

open

## Method

Implement sign and verify with rotation; write-only IAM; hash chain plus a retention-locked anchor; a tamper drill; record real costs over a soak run.

## Unlocks

ADR-006, ADR-007, cost-model reconciliation

## Fallback

Firestore-backed append log plus anchor if BigQuery constraints bite.

## Why unverified

An earlier plan used symmetric HMAC; BigQuery is not immutable; the cost model was contradictory. ADR-006 and ADR-007 are accepted and this spike is verification only.

## Result

Pending. Not yet run; no result is recorded.
