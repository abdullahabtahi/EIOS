# EIOS Data Strategy (platform-level)

**Status**: DRAFT v2, nothing built yet. **Updated**: 2026-10-13. **Owner**: you. **Client**: Deriv (the briefs in `docs/brief/` are theirs). **Companions**: `adk.md`, `synthetic_data_strategy.md` (L0 foundry), `data_products_and_omcp.md` (catalog and contracts), `financial_geospatial.md` (v3, to be restructured).
**Tags**: `[ASSUMPTION]` `[TARGET]` `[ILLUSTRATIVE]` `[EXTERNAL]` (third-party fact; tag pending an ADR). "Verified" = checked 2026-10-13 by reading code or a read-only call. "By reading" = not executed.

> No data strategy, no AI strategy. The data platform and the agentic GIS are domain-agnostic. AML is one bounded context among several, not the boundary. There is no deadline pressure; sequencing is by dependency.

---

## 1. Status board

| # | Workstream | Status | Exit criterion |
|---|---|---|---|
| D0 | Decisions, DDD context map, ADR | ADR-018 drafted as Proposed; needs your review | Section 4 map and section 9 decisions agreed; ADR drafted |
| D1 | Fix data-plane defects R1-R4 (section 3) | In progress: R2 in PR #31, R1 labelling in PR #32 (open); R3, R4 and a deployed data path not started | Vault salt from config and fail-closed; export and warm-start paths agree; governance tables out of the hot DB; a deployed data path exists or the UI says it is fixture |
| D2 | Geo standard on shared objects | Not started | Contracts and foundry carry the section 7 columns |
| D3 | Reference layer (geography, macro, risk lists) with provenance | Not started | Tables pass contracts; every row has source, licence, as-of, snapshot |
| D4 | Warm tier (BigQuery) behind a metric/entity port | Not started | Same metric query answered from hot or warm by freshness need |
| D5 | Market and competitor feed (OpenBB) | Not started | Competitor reference product populated with `[EXTERNAL]` provenance |
| D6 | RAG corpus (statutes, regulator guidance) | Not started | Citations resolve to a document passage |
| D7 | Optional pack: on-chain and OFAC exposure | Not started | Only if Deriv's crypto cashier flows justify it |

D1 and D0 gate everything else. ADK work A0-A3 (`adk.md`) does not wait on D2-D7; it runs on the existing hot state.

## 2. Principles

1. One data platform, many bounded contexts and scenario packs. No tool, table or metric hard-codes a domain.
2. Geo is a dimension of every located object.
3. Agents read named, parameterised tools only. No free SQL for the model.
4. Provenance on every row: source, licence, as-of, snapshot id. Replays reference snapshots.
5. Real where it exists, synthetic where it must be private, never unlabelled. Customer data is synthetic (`[ILLUSTRATIVE]`); reference data is real (`[EXTERNAL]`).
6. External data enters through an anti-corruption layer into reference products, never straight into a context's model.
7. The deployed system must not look live when it is fixture (CLAUDE.md honesty rule).

## 3. Current-state review (what exists, what is wrong)

**Exists and is good**: contracts for 15 products ([models.py](../EIOS/src/eios/contracts/models.py)); seeded foundry generators for all domains plus eval-only truth store and hard negatives; ingestion with contract validation, DLQ, circuit breaker, DQ monitor, token vault, entity resolution ([ingestion/](../EIOS/src/eios/ingestion)); lineage manifests on every export; a versioned metric registry over the DuckDB hot state ([ontology/metrics](../EIOS/src/eios/ontology/metrics)).

| ID | Finding | Severity | Evidence |
|---|---|---|---|
| R1 | **The deployed data plane is not running.** The cockpit image copies `src`, schemas, prompts and spec contracts, no data. No ingestion service is in the Terraform identities. The cockpit server, governance runtime and API app do not load hot state. Workstation payloads are hard-coded (for example `CR84920` in `cockpit/aml.py`), matching CLAUDE.md. | High | services/, infra/, grep (by reading) |
| R2 | **Token vault salt is never taken from config.** `IngestionConfig` defines `hmac_salt` (env `EIOS_HMAC_SALT`), but the processor and router read a field named `token_vault_salt` that does not exist and fall back to a hard-coded literal. Pseudonym tokens therefore derive from a constant in source. | High (security) | [processor.py:62](../EIOS/src/eios/ingestion/processor.py#L62), [router.py:104](../EIOS/src/eios/ingestion/router.py#L104), [config.py:46](../EIOS/src/eios/ingestion/config.py#L46) |
| R3 | **Export and warm-start paths do not line up on defaults.** The exporter writes `<base>/lakehouse/<product>/date=.../`; the loader reads `<base>/raw/<product>/*.parquet` non-recursively, with the same base. | Medium | exporter.py, warm_start.py (by reading, not run) |
| R4 | **One in-memory DuckDB mixes raw products, derived analytics and governance tables** (ledger, intents, WORM checkpoints, simulated write-back). No context boundaries; governance rows are non-durable there while Firestore is the durable ledger. | Medium | [hot_state.py](../EIOS/src/eios/ingestion/hot_state.py) |
| R5 | Hot state evicts at 24 h; the only history is local Parquet. The briefs require historical time series and trend analysis. | Medium | router.py, `data.md` |
| R6 | Queue and hot state are per process. Several Cloud Run instances would each hold different state; there is no shared serving tier. | Medium | queue.py, hot_state.py |
| R7 | Geo is two strings (`country`, `region`); no geography, coordinates or cells. | Low | contracts/models.py |

Not examined: ingestion test results, benchmarks, `ontology/core/hydrator`, the graph engine's data access.

## 4. DDD context map (proposal, needs your review)

| Context | Brief | Code today | Core aggregates |
|---|---|---|---|
| Financial-crime monitoring | `monitoring.md` | `aml/` | Alert, Case, WithdrawalAssessment |
| Partner retention | `churn.md` | `churn/` | PartnerHealth, CohortAlert |
| Partner integrity | `fraud.md` | `fraud/` | Ring, OppositeTradePair, FraudCase |
| Enterprise intelligence | `data.md` | `synthesis/` | Forecast, Scenario, Briefing |
| Governance and decisions | all | `ontology/actions/`, cockpit governance | ActionIntent, LedgerEntry, Approval |
| Data platform | `data.md` capability 1 | `ingestion/`, `contracts/`, metrics | DataProduct, Contract, MetricDefinition |
| Conversation (application layer) | `data.md` capability 4 | `conversation/` (to ADK) | Session, Turn, EvidenceBundle |

**Shared kernel**: identity (client, partner ids and identity-cluster tokens), geography, time and as-of provenance, metric definitions. **Relationships**: contexts exchange data only through published contracts and OMCP tools (customer-supplier); external sources (OpenBB, public datasets, regulator lists) enter through an anti-corruption layer into reference products. **Consequence**: separate schemas per context (DuckDB schemas now, BigQuery datasets later) and governance data out of the analytics DB.

## 5. Tiers and target architecture

| Tier | Store | Holds | Serves |
|---|---|---|---|
| Hot (seconds to ~24 h) | DuckDB in-process, fed by Pub/Sub | live events, streaming detection, what-if (RL-6 under 200 ms `[TARGET]`) | detectors, scenario engine |
| Warm (days to years, queryable) | BigQuery, partitioned and clustered | history, cohorts, time series, vector index | agent tools via MCP Toolbox, trends, regional analytics |
| Cold and evidence | GCS Parquet with lineage plus BigQuery snapshots | replay bundles, audit evidence | proof bundles |
| Governance | Firestore plus WORM anchors | ledger, approvals, nonces | intent hub (never the hot DB) |

```
Pub/Sub ► validate (contracts, DLQ, DQ, ER, vault) ┬► hot DuckDB (per-context schemas)
                                                   ├► BigQuery warm (subscription / micro-batch)
                                                   └► GCS Parquet + lineage
reference sources ► ACL ► reference products (with provenance) ► BigQuery
all tiers ► metric/entity port (picks tier by freshness need) ► MCP Toolbox / function tools ► ADK agent
```
Open question: which tier serves live agent answers (D-2). Cost guard for public tables: partition filter, dry run, `maximum_bytes_billed`.

## 6. Reference sources (anti-corruption layer inputs)

| Source | Where | Verified | Licence state | Serves |
|---|---|---|---|---|
| Overture Maps (release 2026-09-23_1) | `bigquery-public-data.overture_maps` | yes | confirm attribution | geography |
| World Bank WDI, Google Trends, WorldPop | `bigquery-public-data` | listed | confirm | macro, demand, population |
| CFPB complaints, FDIC banks, SEC quarterly financials | `bigquery-public-data` | listed | confirm | conduct, competitor |
| OpenBB ODP | separate service; Apache-2.0 software, data terms per provider | licence page read | per provider | market, competitor |
| OFAC SDN | download (19,431 lines; 106 entries with digital-currency addresses) | yes | US government publication; confirm | sanctions exposure (D7) |
| FATF jurisdiction lists | hand-curated small table | no | confirm | geo risk |
| On-chain (`crypto_ethereum`, `crypto_bitcoin`, ~20 more) | `bigquery-public-data` | yes | public dataset | D7 only |
| ICIJ Offshore Leaks, GLEIF, OpenSanctions, Elliptic, IBM AMLworld | downloads | v2 spike or no | ODbL / unknown / CC BY-NC / unknown | optional; verify first |
| Statutes and guidance | documents | no | confirm per source | RAG |

Deriv's brief is about behavioural patterns in its own data (round-trip trades, KYC-to-withdrawal timing, device and IP rings); that data is the synthetic private layer. Public data supplies context, not detection. Reconcile with L0: synthetic competitors stay aliases; real listed competitors are a separate reference product.

## 7. Geo standard (every located product)

`country_iso` | `admin1` | `geog` (BigQuery GEOGRAPHY) | `cell_id` | `geo_precision` | `geo_source`. BigQuery has GEOGRAPHY, `ST_*` and S2 (verified) and no native H3 (verified: `H3_LATLNGTOCELL` not found); use S2 or compute H3 in a job. Entity and jurisdiction level only; no natural-person names or street-level geocoding.

## 8. Scenario packs (same platform)

| Pack | Question | Main data |
|---|---|---|
| Financial-crime | Where is this ring's money going? | foundry transactions, devices, KYC; optional OFAC and on-chain |
| Regional executive | Why is client LTV declining in APAC? (`data.md`) | WDI, Trends, competitors, partner and churn products |
| Partner risk | Which regional cohorts decay together? | geography, WDI, competitor moves |
| Operations | Where is regional capacity tight? | `platform_operations` |

## 9. Open decisions

| ID | Decision | Recommendation | Status |
|---|---|---|---|
| D-1 | Restructure `financial_geospatial.md` v3 into v4 (platform, contexts, packs) | Yes | Open |
| D-2 | Which tier serves live agent answers; BigQuery behind Toolbox vs DuckDB with a small MCP server | Hot for live detection and what-if; BigQuery for history and analytics; decide per metric by freshness | Open |
| D-3 | Regulators in the RAG corpus | Follow Deriv's real licensing jurisdictions (not yet verified) | Open, needs you |
| D-4 | On-chain and OFAC pack | Optional; only if Deriv's crypto cashier flows justify it | Demoted |
| D-5 | OpenBB shape (service vs MCP server) | Defer until the regional-executive pack | Open |
| D-7 | Add `[EXTERNAL]` provenance tag | ADR | Open |
| D-8 | Approve the section 4 context map | Review needed | Open, needs you |

## 10. Risks

| Risk | Mitigation |
|---|---|
| UI looks live while data is fixture (R1) | D1: wire or label |
| Real-person harm from public data | Policies P-1..P-5 (v3); claims limited to list membership and observed facts |
| BigQuery cost | Partition filters, dry run, byte cap, bounded slices |
| Licence mistakes | Register every source here before ingestion |
| Context boundaries ignored again | Per-context schemas; contract tests per context |

## 11. Corrections
- OpenBB V5 is Apache-2.0 (V4 and earlier AGPL). `CLAUDE.md` and `financial_geospatial.md` section 8.2 still say AGPL; to fix. Data terms stay per provider. The repository now lives at `openbq-org/OpenBB`.
