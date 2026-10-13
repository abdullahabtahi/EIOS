# ADR-018: Bounded contexts and a single governed tool surface

## Status

Proposed

## Date

2026-10-13

## Context

EIOS serves the four Deriv challenge briefs (`docs/brief/`): financial-crime monitoring, partner retention, partner integrity and enterprise intelligence. The code already has a module per domain, but nothing enforces the boundaries between them, and the agent layer ignores the ontology it was built to sit on:

- One in-memory DuckDB (`ingestion/hot_state.py`) holds raw data products, derived analytics tables and governance tables (ledger, intents, WORM checkpoints, simulated write-back). Governance rows there are non-durable while Firestore is the durable ledger.
- The copilot (`conversation/copilot_engine.py`) calls fixture functions in `conversation/tools.py` directly. It bypasses the OMCP server (`ontology/omcp/server.py`), which carries caller roles and security markings, and the LangGraph specialists use a third, different tool vocabulary.
- External and public data has no defined entry point into the model.
- The review recorded in `docs/data-strategy.md` section 3 (R1 to R7) shows the consequences: the deployed UI looked live on fixture data, and the token vault was keyed by a constant.

Palantir's AIP draws the same line: agents act only through typed ontology tools (object query, function, action), and the ontology is the single interface over data and permissions.

## Options considered

- **A. Keep the shared hot DB and let each consumer bring its own tools.** No change cost. Cons: the boundary violations above persist, every new consumer (the ADK agent, an MCP client, the UI) reimplements tool logic, and markings can be bypassed.
- **B. Bounded contexts with per-context schemas, a small shared kernel, and OMCP as the only agent-facing tool surface (chosen).** Cons: a migration of table ownership and one more interface to maintain.
- **C. A deployable service per context now.** Strongest isolation. Cons: operations cost and latency for a small team, loses the sub-200 ms in-process what-if path, and scale-to-zero friction. Not needed to get the benefits of B.

## Decision

Adopt option B.

1. **Contexts**: financial-crime monitoring (`aml/`), partner retention (`churn/`), partner integrity (`fraud/`), enterprise intelligence (`synthesis/`), governance and decisions (`ontology/actions/`, cockpit governance), data platform (`ingestion/`, `contracts/`, metrics) and conversation (`conversation/`, an application layer).
2. **Shared kernel**: identity (client and partner ids, identity-cluster tokens), geography, time and as-of provenance, metric definitions. Nothing else is shared.
3. **Relationships**: contexts exchange data only through published contracts and OMCP tools. External sources (OpenBB, public datasets, regulator lists) enter through an anti-corruption layer into reference products that carry source, licence, as-of and snapshot columns.
4. **Storage**: each context owns a schema (DuckDB schemas now, BigQuery datasets for the warm tier later). Governance data leaves the analytics database; the intent hub's durable store stays the source of truth.
5. **One tool surface**: every consumer that acts on behalf of an operator, including the ADK agent and any external MCP client, goes through OMCP. OMCP exposes typed tools in three kinds: object and metric queries, deterministic functions, and propose-only actions. There is no execute tool, no generic SQL tool, and markings and caller role are enforced there. The fixture tools are removed once their OMCP replacements exist. Implementation moves to the official MCP SDK when the migration reaches that step.
6. **Out of scope here**: the choice of agent runtime (superseding ADR-016, a separate ADR), and which tier serves live answers (data-strategy decision D-2).

## Consequences

- Positive: boundaries become testable (contract tests per context); one place enforces markings; the agent cannot reach data the operator cannot; external data cannot silently become part of a context's model.
- Positive: the same tool surface serves the UI, the ADK agent and external MCP clients.
- Negative: table ownership has to be migrated; OMCP becomes a critical interface needing versioning and contract tests (additive changes only within a major, per `data_products_and_omcp.md`).
- Follow-ups: per-context schemas in `hot_state`; move governance tables out of the analytics database; retire `conversation/tools.py`; extend the contract tests to the tool catalog.

## Evidence

`docs/data-strategy.md` section 3 (review of the current data architecture, by reading code); `docs/data_products_and_omcp.md` (catalog and OMCP contracts); Palantir AIP agent tools and retrieval-context documentation (read 2026-10-13). No benchmark yet; a latency check of the OMCP path against the agent turn budget is part of the first ADK slice.

## Revisit when

A second team owns a context, a context needs independent scaling or release cadence, or the in-process what-if path no longer meets its latency target.
