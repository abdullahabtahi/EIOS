# S-01: LLM availability, pricing, caching and limits

## Id

S-01

## Question

Which LLM(s), model IDs, pricing, context caching and rate limits are actually available and affordable?

## Time box

At most 1 day [TARGET] metric: spike_duration, reported in the Result section when the spike runs.

## Owner

Platform lead [ASSUMPTION] owner: engagement lead; verify by S0 kickoff.

## State

open

## Method

Query provider docs and console; run a short latency and cost benchmark through the gateway with tool calling and structured output `[ASSUMPTION]` owner: platform lead; verify by the spike run.

## Unlocks

ADR-002 (LLM gateway & default models)

## Fallback

Provider-agnostic gateway; default to the best verified model per role (router vs synthesis).

## Why unverified

An earlier plan pinned a model name without verification.

## Result

Pending. Not yet run; no result is recorded.
