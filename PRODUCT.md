# Product

Inferred from the repo (CLAUDE.md, `docs/brief/`, DESIGN.md), not from an interview. Correct anything that is wrong.

## What it is
EIOS, the Enterprise Intelligence Operating System: an operator cockpit for a regulated fintech (client persona: Deriv). Analysts triage signals, read an evidence dossier, work a canvas (graph, radar, SAR composer, ledger), and stage governed actions that a second human approves.

## Users
- AML investigators working dozens of alerts a day with regulator exposure.
- Partner managers watching churn hazard and value at risk.
- Compliance and audit reviewers (ledger, hash chain, approvals).
- Data operations (ingestion SLOs, red-line gates) and executives (briefing, what-if).

All are expert, keyboard-comfortable, and accountable for what they approve.

## Mode
Operate: scanability, consistency and honesty outrank expression.

## Product promise
Nothing is trusted unless it is verified. Every figure is computed by a deterministic engine, traces to a source and an as-of time, and any state change is a signed, expiring, four-eyes-approved Action Intent.

## Tone
Calm, precise, institutional. Plain operator language (case, network, alert), not invented jargon. Confident without decoration.

## Anti-references
Generic AI dashboards: rainbow status chips, boxes inside boxes, glow, gradient text, decorative icons.

## Design principles
1. Object first: entities are the unit, every figure links to its object and lineage.
2. One dominant task per screen.
3. Colour means state.
4. Preserve what works: refine with evidence, never restyle wholesale.
5. Honest status: outages, replays and unknowns are stated, never masked.
6. Keyboard first.
