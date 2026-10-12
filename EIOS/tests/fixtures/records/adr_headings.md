# ADR-010: Approval service hosting

## Status

Superseded by ADR-020

## Date

2026-01-05

## Context

Approvals need a durable, single-use intent store.

Second paragraph of context.

## Options considered

- A: Cloud Run plus Firestore
- B: Self-managed queue

## Decision

Cloud Run plus Firestore.

## Consequences

Operational simplicity.

## Evidence

S-06

## Revisit when

Approval volume exceeds the free tier.
