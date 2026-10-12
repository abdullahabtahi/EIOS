# S-05: Graph scale ceiling for NetworkX + Louvain and hub-suppression effectiveness

## Id

S-05

## Question

What is the graph scale ceiling for NetworkX plus Louvain, and how effective is hub suppression?

## Time box

At most 1 day [TARGET] metric: spike_duration, reported in the Result section when the spike runs.

## Owner

Platform lead [ASSUMPTION] owner: engagement lead; verify by S0 kickoff.

## State

open

## Method

Generate graphs of increasing edge count `[ASSUMPTION]` owner: data science lead; verify by the spike run. Time graph build and community detection; compare naive and hub-suppressed rings.

## Unlocks

ADR-004 (graph engine), ADR-012

## Fallback

Snapshot warm start; Spanner Graph or Neo4j as the documented alternative.

## Why unverified

An in-memory graph versus a serverless runtime, and shared-IP false merges.

## Result

Pending. Not yet run; no result is recorded.
