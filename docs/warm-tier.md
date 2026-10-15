# Warm tier on BigQuery (data-strategy D4, decision D-2)

Status: design, 2026-10-15. Branch `feat/warm-tier`. Companion: `docs/data-strategy.md` (tiers, principles), `docs/operations-engine.md`.

## Why

The ontology's history had nowhere to live: hot state is in-memory DuckDB and the synthetic worlds are rebuilt at every start. A warehouse that the assistant reads through the governed port makes the platform real: contract-validated events land in partitioned, clustered, lineage-stamped tables, and answers about history come from them, labelled `warm`. The customer rows stay synthetic (`[ILLUSTRATIVE]`); the pipeline is real.

## Decision D-2 (which tier answers what)

Hot (DuckDB) answers live detection, what-if and the recent window. BigQuery answers history beyond the hot window and reference data. The rule is a window start older than the hot retention (`EIOS_HOT_RETENTION_DAYS`, default 7 `[ASSUMPTION]`) goes warm. The model never writes SQL: it calls named, parameterised capabilities (data-strategy principle 3).

## Flow

```
foundry world -> contract events -> IngestionPipeline (validate, DLQ) -> hot state (DuckDB)
                                              |-> ParquetLakehouseExporter (date partitions + lineage)
                                                       -> BigQueryWarmSink load job -> warm_<context>.<product>
                                              |-> breaches -> warm_dlq.quarantined (reason, raw payload hash)
assistant -> tool port capability -> WarmStore (named query, dry run, byte cap, partition filter) -> BigQuery
```

- **Schemas come from the contracts.** `contracts/models.py` (15 pydantic products) generates the BigQuery schema, so DDL cannot drift. Every table is partitioned by day on the event timestamp and clustered by the entity key; every row carries `_batch_id`, `_loaded_at`, `_source` from the exporter's lineage manifest.
- **Load jobs, not streaming inserts.** Free, idempotent per batch id, and fits micro-batching. Streaming is not worth its cost at this volume.
- **A seam for offline.** `WarmStore` and `WarmSink` are protocols: the BigQuery implementation, and a local one that runs the same query catalogue over the Parquet lakehouse with DuckDB, so unit tests, CI and a laptop need no cloud. The queries use portable SQL only.
- **Cost guard.** A query without a partition filter is refused; every query is dry-run first and refused above `EIOS_WARM_MAX_BYTES` (default 100 MB `[ASSUMPTION]`). The bytes billed go in the result.
- **Honesty.** A result carries the origin of the plane its rows came from (`engine`, as for every AML figure), the as-of, and a `source` that names the warehouse and table (`warm.bigquery:<project>.warm_aml.transactions_aml`), which a figure's popover shows. There is no separate `warm` origin: the numbers are the engine world's, loaded through the pipeline. An unreachable warehouse is `DATA_UNAVAILABLE` with its reason, never a silent fall-back to hot that would hide the gap.

## First use case

`get_account_history(entity_id, days)`: daily deposit and withdrawal totals and the largest transactions for one account over the world's full span, from `transactions_aml`. The assistant can answer "how has this account's activity trended" with figures that trace to a warm result. It needs a description (no digits), a row in `agent_gates/capability_map.yaml`, an offline route and a safety sample, as for any capability.

Second use case, for the geospatial feature: reference geography (boundaries and places) from public datasets into a `warm_reference` dataset with source and as-of on every row. Out of scope for this milestone beyond the dataset and table naming.

## Tasks

1. Contract to BigQuery schema generator, pure and tested; one test per product that the schema accepts the contract's own example.
2. Terraform module `bigquery_warm` (datasets, tables from the generated schema, DLQ table, byte-cap-friendly settings, IAM for the API identity: job user and data viewer) plus a dev sandbox root; plan shown, dev apply allowed, prod-like apply is the owner's.
3. `WarmSink` (BigQuery load job from the exporter's Parquet and lineage; local double) and the loader that runs a world through the pipeline into it.
4. `WarmStore` with the named-query catalogue, dry run, byte cap, partition filter; local double.
5. `get_account_history` capability and its four registrations.
6. Parity eval: the same window answered from hot and from warm must agree, judged against what the world planted. Measured, not asserted.
7. Deploy wiring: env vars (`EIOS_WARM_DATASET`, retention, byte cap), roles, runbook lines. A deploy is the owner's say-so.

## Not in this milestone

BigQuery Graph (spike S-BQG-1, needs an Enterprise reservation, measure first), vector search, reference-data ingestion, streaming, and telemetry (the board's agent objectives stay on the in-memory window).

## Built and measured (2026-10-15)

- **Schema and Terraform.** 14 product tables plus a quarantine table, generated from the contracts; applied in the dev sandbox project (5 datasets, 15 tables, each with `require_partition_filter`). A test fails if `tables.json` drifts from the contracts.
- **Load.** The AML world's 17,646 transactions go through the real ingestion pipeline and into the local double in 8.3 s `[MEASURED]`. A history load plants no breaches, so the history is exact; `plant_breaches` shows quarantine at work (71 of 17,644 events at the board's 0.4% rate, each kept with its reason and a hash of the payload, never the payload).
- **Query definition.** An account's deposits and withdrawals count completed and pending money, never failed or cancelled. The first version counted completed only and the parity eval caught it: the engine counts a pending withdrawal, and three story accounts disagreed.
- **Parity eval** (`tests/dataplane/test_warm_parity.py`). Over the 124 busiest accounts by deposits or withdrawals, warm 30-day totals equal the engine's own `dep_volume` and `wd_volume` to the cent `[MEASURED]`. With breaches planted, each shortfall equals a quarantined deposit's amount exactly. A second catch: the world stamps a few story events up to two hours after its as-of, so the loader takes everything the world holds (not "720 hours back", which dropped the first two hours of history) and the tool's window allows a day past the as-of.
- **Capability.** `get_account_history` is offered to the AML workstation (13 capabilities; the cap of 12 was an assumption and was raised by one, to be watched in the live baseline). In a live check the model chose it for "how has this account trended over the last 30 days" and "did deposits spike in the past two weeks", and the answers carried the warehouse source; a plain dossier question did not call it `[MEASURED]`, 3 turns.
- **Cost guards.** A query without a partition filter is refused by BigQuery itself; every query is dry-run first and refused over `EIOS_WARM_MAX_BYTES` (100 MB `[ASSUMPTION]`); the real run carries the same cap.

## Still to do

Load the history into the dev and prod-like warehouses (`python -m eios.warm load --backend bigquery --project <id>`), apply the module in prod-like with the API as reader, set `EIOS_WARM_BACKEND=bigquery` and `EIOS_WARM_PROJECT` on the API service, and read a real BigQuery dry-run byte count into this note. Until then the deployed demo uses the local double, which the note and the `source` string say.
