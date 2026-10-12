# S-07: Entity-resolution approach adequacy (deterministic + probabilistic)

## Id

S-07

## Question

Is the entity-resolution approach (deterministic plus probabilistic) adequate?

## Time box

At most 1 day [TARGET] metric: spike_duration, reported in the Result section when the spike runs.

## Owner

Platform lead [ASSUMPTION] owner: engagement lead; verify by S0 kickoff.

## State

open

## Method

Seed duplicates with noise; compare rules against Fellegi-Sunter (for example Splink).

## Unlocks

ADR-008 (entity-resolution approach)

## Fallback

Deterministic keys plus a review queue.

## Why unverified

The brief requires entity resolution and data-quality flags; the earlier plan gave no design detail.

## Result

Pending. Not yet run; no result is recorded.
