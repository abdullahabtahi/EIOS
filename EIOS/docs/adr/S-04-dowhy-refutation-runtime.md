# S-04: DoWhy refutation runtime and stability on our DAG size

## Id

S-04

## Question

What are the DoWhy refutation runtime and stability on our DAG size?

## Time box

At most 1 day [TARGET] metric: spike_duration, reported in the Result section when the spike runs.

## Owner

Platform lead [ASSUMPTION] owner: engagement lead; verify by S0 kickoff.

## State

open

## Method

Time a nightly fit and refute on synthetic history across a range of edge counts; measure variance across seeds.

## Unlocks

ADR-005 (causal engine & caching)

## Fallback

Cache the nightly results; the live path uses parametric propagation only.

## Why unverified

Refutation is not sub-second; an earlier plan implied live use.

## Result

Pending. Not yet run; no result is recorded.
