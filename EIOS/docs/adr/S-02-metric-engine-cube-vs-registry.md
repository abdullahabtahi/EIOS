# S-02: Cube Core vs lightweight metric registry over DuckDB

## Id

S-02

## Question

Cube Core vs lightweight metric registry over DuckDB: which fits?

## Time box

At most 1 day [TARGET] metric: spike_duration, reported in the Result section when the spike runs.

## Owner

Platform lead [ASSUMPTION] owner: engagement lead; verify by S0 kickoff.

## State

open

## Method

Stand up both on a small set of KPIs `[ASSUMPTION]` owner: platform lead; verify by the spike run. Measure cold start, memory, query latency and operational surface.

## Unlocks

ADR-003 (metric engine)

## Fallback

The registry contract is the invariant; the engine is swappable.

## Why unverified

Cube needs a Node service plus CubeStore/Redis, a poor fit for scale-to-zero, and adds operating cost.

## Result

Pending. Not yet run; no result is recorded.
