# ADR-010: Approval service on Cloud Run + Firestore; Cloud Workflows only for scheduled jobs

## Status

Accepted

## Date

2026-10-02

## Context

Action Intents move through propose, approve and execute (`initial_plan.md` section 6.1). The v2 plan used Cloud Workflows as the state machine. `docs/red_team_findings_v3.md` (finding 9, severity High) and the plan record that Workflows is a poor fit for interactive human approval. This ADR is a backfill of that decision.

## Options considered

- Cloud Workflows as the approval state machine (the v2 design). Drawback: a poor fit for interactive human approval, per the plan.
- Approval service on Cloud Run with state in Firestore; Workflows kept only for scheduled jobs such as the Morning Briefing and the nightly SCM refit (chosen). Drawback: the team writes and tests the state machine itself `[ASSUMPTION]` owner: platform lead; verify by the approval-service skeleton tests.

## Decision

Hold the approval state machine in an approval service on Cloud Run with Firestore state. Cloud Workflows is retained only for scheduled jobs.

## Consequences

- Positive: interactive approval, RBAC and optional four-eyes review fit a service with its own state; Firestore also holds the replay-protection records from ADR-006.
- Negative: state-machine correctness is the team's responsibility, not a managed product's.
- Follow-ups: cover the state machine with tests, including expiry and single-use behaviour.

## Evidence

**Backfilled** from `initial_plan.md` section 6.1 and `docs/red_team_findings_v3.md` (finding 9). No spike is attached.

## Revisit when

approval load or latency needs exceed what the service can meet, or the interactive-approval requirement changes.
