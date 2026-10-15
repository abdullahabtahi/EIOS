# Geospatial: milestones after the scaffold

Status: plan for review. Product direction is in `docs/financial_geospatial.md`; this note only orders the work and says where to stop and decide.
Rule for every milestone: one branch, one PR, tests first, a result reported as measured. A lens that does not shorten an investigation is cut.

## Done: M0 scaffold (branch `feat/geo-scaffold`, not yet committed)
Geospatial section at `/cockpit/geospatial`: Google vector map with deck.gl (`@vis.gl/react-google-maps`, `GoogleMapsOverlay`), three lenses (jurisdiction risk, corridors, IP vs KYC country), widgets, a copilot placeholder that says it is not connected. Data is a fixture. The backend runs locally against the dev project (Firestore, BigQuery warm tier, Vertex, Model Armor, KMS).

## Milestones
M1 notes: the map uses a built-in muted light style on a raster map, so no console-created Map ID is needed; set `NEXT_PUBLIC_GOOGLE_MAP_ID` to use a cloud-styled vector map instead. Hover and click were verified with a scripted Chrome session, not only unit tests.

| # | Milestone | Done when | Needs a decision first |
|---|---|---|---|
| M0.5 | Land the scaffold: commit, PR, green CI | Merged | Your go to merge |
| M1 (built, awaiting your review) | Reference layer in BigQuery (`warm_reference`): Overture boundaries, curated FATF tier table, ICIJ counts per jurisdiction, World Bank indicators; source and as-of on every row; named queries under the byte cap | Clicking a country shows real facts with source and as-of | None |
| M2 (built, measured) | Geo-enabled private world: `ip_country` and counterparty country on the contracts and foundry, denser accounts with city-level location, planted stories and their truth table, warm reload | Plane check logged as measured against planted truth, with precision and recall per lens | None (synthetic, country-level) |
| M3 | Engine endpoint and live map: `/api/cockpit/aml/geo`, map reads it, fixture removed | Map and widgets equal the engine's numbers; empty data shows `NO_DATA` | None |
| **Gate G1** | Choose the lead persona from the stories: MLRO exposure control tower, or investigator drill-down | A written choice | **Yes, yours** |
| M4a | If MLRO: exposure by tier and a re-tier what-if that reuses the what-if engine | Under the 200 ms propagation line with attribution summing to 100.0% | G1 |
| M4b | If investigator: Entity 360 link and draw-to-set into the triage queue | Click and draw open the existing inspector and queue | G1 |
| M5 | Geo agent: `get_geo_signals` and `get_corridors` with the four registrations, map context in the turn, closed-enum map intents, golden cases | Agent gates green; no figure typed by the model | M3 |
| M6 | Governed action from a map selection, SAR geography paragraph, evidence bundle with replayable as-of | Hold staged and four-eyes approved from the map; SAR cites every geo figure | M5 |
| Opt | Restricted-jurisdiction control (prohibited countries behind a VPN) | Only meaningful with real IP geolocation; do not demo on synthetic data | Real data source |

M1 and M2 are independent and can run in parallel. M4a and M4b are alternatives, not a sequence.

## Housekeeping, outside the milestones
- Retire the `[ILLUSTRATIVE]` tag: edit CLAUDE.md section 5 and the `label_check` gate in a separate small PR.
- Fix stale CLAUDE.md lines: the legacy gcloud default project, and the rule about using other ports.
- Add `scripts/dev_gateway.sh <project-id>` so the local backend starts with one command.
- Investigate the slow local copilot turns (the first two took 21 s and 15 s against about 2 s measured earlier; 11.8 s sat under `other` on the first).
- Delete the inactive gcloud configuration `default` that points at the legacy project, if wanted.

## What is deliberately not planned
Satellite imagery, generic heatmaps with no decision attached, OpenBB (revisit with the OpenBB section), a second agent runtime, and the CARTO library (revisit at M5 for view-state validation only).

## M2 results

The AML world now carries `geo_flows` (one row per transaction: login country and payment-instrument country) and a separate planted geo truth: two story rings that log in from one shared foreign gateway, 60 benign travellers who also log in from abroad, and structuring and wash accounts routed through Myanmar and the British Virgin Islands. A guard test holds every pre-existing frame byte-identical (clients, transactions, trades, edges), and the transaction contract and warehouse tables are untouched.

`python -m eios.dataplane.geo_plane` builds the geo engine over the served world, tiered from the live reference layer, and prints the measured quality:

| Lens | Result `[MEASURED]` |
|---|---|
| IP vs KYC mismatch | 50 clients flagged, precision 1.00, recall 0.77 of the 3,341 assessable clients and 0.74 of the malicious ring members |
| Risky corridors | 20 flagged, precision 1.00, recall 0.69; every planted corridor surfaces as elevated |
| Geo score, top 50 | precision 0.70 against a base rate of 0.017, lift 41.7x |

What the first run taught: the original rule (share of foreign logins at least 0.5) gave precision 0.81, because ordinary clients with 3 to 5 events cross a 50% share by chance. The original recall target of 0.8 was unreachable for a structural reason: 44% of clients have fewer than 3 events, so no per-client test can judge them, and wash accounts have exactly two transactions. Both lenses now use one binomial test against the population base rate, and "assessable" is derived from the same statistics (could every event being foreign reach significance), so a client that cannot be judged is reported as not assessable, never as clean. Precision and lift targets were met as written; the recall targets were replaced, with the diagnosis recorded in `tests/dataplane/test_aml_geo_engine.py`.

Open from M2: the lens cannot see sparse ring members one at a time. A ring-level lens (many clients sharing one foreign login country) would recover them and is the natural content of the investigator drill-down (M4b).
