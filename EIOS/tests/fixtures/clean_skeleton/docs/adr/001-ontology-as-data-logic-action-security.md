# ADR-001: Ontology as data + logic + action + security (not just a semantic layer)

## Status

Accepted

## Date

2026-10-02

## Context

The platform needs a shared model of the enterprise that both humans and AI agents operate on. This ADR is a backfill: the decision was taken in the planning workspace before the repository existed, and is recorded here with its sources. `docs/foundry.md` states that the Ontology is not a semantic layer; it represents the interconnected decisions of an enterprise through the four-fold integration of data, logic, action and security, with object types, link types, action types, functions and interfaces. CLAUDE.md invariants 5 and 6 (no autonomous write-back; data consumed as products via the Ontology API, never raw tables) depend on actions and security being part of the model itself.

## Options considered

- Semantic layer only (objects, properties and links over datasets, with no logic, action or security modelling). Drawback: it cannot express governed actions or security markings, so write-back control and access rules would live outside the model `[ASSUMPTION]` owner: architecture lead; verify by the first action-type design review.
- Four-fold Ontology: data, logic, action and security modelled together (chosen). Drawback: more to design and build before the first module runs, and the model must stay consistent across four concerns `[ASSUMPTION]` owner: architecture lead; verify by the F01 ontology review.

## Decision

Model the Kinetic Enterprise Ontology as the four-fold integration of data, logic, action and security, per `docs/foundry.md`, and not as a semantic layer only.

## Consequences

- Positive: agents and the cockpit share one governed model; action types and security markings are first-class, which supports the no-autonomous-write-back and data-as-a-product invariants.
- Negative: the ontology scope is larger than a metrics layer, so the first slice carries more design work.
- Follow-ups: define the object, link and action types per `docs/data_products_and_omcp.md`; enforce markings in the Ontology API, not in prompts.

## Evidence

**Backfilled** from `docs/foundry.md` (Ontology Layer section) and the ADR index in `docs/spikes_and_adrs.md`. No spike is attached to this decision.

## Revisit when

the ontology cannot express an action or security rule that a module needs, or a delivery slice shows the four-fold scope is not affordable.
