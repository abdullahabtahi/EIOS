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
| M3 (built, awaiting your review) | Engine endpoint and live map: `/api/cockpit/geo/flows`, map reads it, fixture removed | Map and widgets equal the engine's numbers; empty data shows `NO_DATA` | None |
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

## M3 notes

`GET /api/cockpit/geo/flows` serves the geo engine's corridors (with jurisdiction tiers), flagged IP-versus-KYC country pairs and tier exposure; the fixture is gone. The map places every flow with the reference layer, so a flow whose country cannot be placed is skipped, and with no reference layer no flow is drawn. The evaluation against the planted truth stays in logs and the CLI and is not part of the payload; a corridor whose tier is unknown is `null`, never `low`. Each lens is disabled, with the reason stated, when the data it needs is missing. The first flows request builds the engine's view (about 10 s) and later ones are served from memory.

The map opens on the volume-weighted centre of the corridors, because the seeded world's money moves mostly between South and Southeast Asia and the Gulf; drawing every flow at world scale is unreadable. Arcs are limited to every elevated corridor, the six largest others and the ten largest flagged pairs; the widgets keep the full figures.

## UX pass after M3 (first-visit experience)

Reviewed against the first screenshot of the live page: all four lenses, every arc, a legend, a copilot placeholder and seven equal-weight widget sections opened at once, with `ENGINE` and `REFERENCE` tags that mean nothing to a viewer. The design review used the Overview first, zoom and filter, then details on demand sequence, and the Palantir Foundry Map layout (layers on one side, selection on the other, the map as the canvas) as reference.

What changed:
- **One question at a time.** Three views replace four checkboxes: Corridors (opens by default), Login vs KYC, Jurisdictions. Each opens with only its own marks and its own camera framing, and its question is the panel heading, so a first-time reader knows what they are looking at. The old checkboxes survive as a collapsed "Layers" row for the analyst who wants a different mix.
- **Where to look first.** A ranked list per view, in the same order the map draws (so the arc on the map is the row you can click). Clicking a row pins its facts and moves the map to it; a corridor outside the drawn set is drawn when picked. Hover gives a short card beside the pointer (title and three facts), click pins the full set, Esc puts it down.
- **Less on the map.** Arcs are budgeted per kind (10 high, 4 medium, 4 other), so a crowd of one tier cannot hide another, and the legend lists only the marks that are on the map and how many of the data it draws ("Showing 18 of 60 corridors"). Colour carries risk only: red and amber for elevated corridors, a quiet grey for the rest (a green arc read as "safe", which no figure here claims). Arc widths and basemap labels are quieter.
- **Removed.** The `Engine` and `Reference` tags, the "Not connected" copilot card (it returns with M5, when it is connected), the duplicated page subtitle, per-section icons, and the standalone "FATF lists", "Top corridors" and "Offshore entities" widgets, now the Jurisdictions and Corridors lists. Sources stay one click away with the as-of date visible.
- **Same shell as the workstations.** The dark chrome row (brand, clearance tag, operator) is now one shared component used by both headers. The telemetry and Ask controls are not shown on this page because they need workstation state; a dead button would be worse than none.
- **States.** A loading skeleton and a status line while the engine builds its first view (about 10 s), plain-language errors with a Retry button, and `NO_DATA` for an empty result, never zero.

Verified in headless Chrome against the live backend: hover and click on country and arc, lead selection and camera move, all three views, the dark header, no console errors. The legend is hidden below the `sm` breakpoint; the page stacks map over panel on narrow screens. Not done: the Caribbean offshore centres are off-screen on the Corridors view until the analyst pans (the Jurisdictions view opens on the world), and the per-client lens still cannot see accounts with fewer than 3 events.

## N0 to N2 (branch `feat/geo-graph-n0-n2`, stacked on `feat/geo-scaffold`)

Plan agreed after the UX pass: build one loop (trigger, investigate, act, prove) and stop after N2 for review. N3 (SAR geography paragraph, governed hold from the map, evidence bundle on BigQuery snapshots) is not started.

### N0: shareable state and honest coverage
The URL holds the view and the pick (`view=logins&sel=account:CR11568`; kinds `country`, `corridor`, `mismatch`, `gateway`, `account`; anything else in the URL is ignored). The server page passes the search string down so the first render matches on both sides. Each lens states how many clients it can judge (3,341 of 6,000 for login vs KYC `[MEASURED]`); an unflagged client the lens cannot judge is not read as clean.

### N1: login sessions, session lenses, BigQuery Graph
**World.** Every transaction is made in a login session, and clients also log in without transacting: 47,984 sessions `[MEASURED]`, each through a synthetic gateway (home broadband line, carrier NAT, hotel network, VPN exit; `GW-<country>-<kind><n>`, country level only). Planted: one shared VPN exit per mule ring (all six rings, exits in NG, AE, IQ, TR, ZA, PK), and a controller who works members' accounts from that exit within hours of the holder logging in at home; travellers make one trip with no session close to its ends; 140 privacy-minded clients share one commercial VPN exit used by more than 100 accounts, the same shape as the carrier NAT gateways RL-4 suppresses. Clients, transactions, trades and edges stay byte-identical.

**Engine lenses** (`dataplane/aml_geo_sessions.py`), measured on the served world against the planted truth, with real Overture centroids from the reference layer:

| Lens | Result `[MEASURED]` |
|---|---|
| Shared foreign exit (non-hub gateway abroad used by 3 or more accounts that live elsewhere; 2 or more sessions through it) | 71 flagged, precision 1.00, recall 0.99 of 72 ring members; recovers all 7 ring members the per-client lens cannot judge |
| Impossible travel (consecutive sessions further apart than 1,000 km/h allows, 500 km or more) | 58 flagged, precision 0.72, recall 0.58; counting jumps through hubs too (no RL-4) flags 63 at precision 0.67 and 21 benign accounts instead of 16 |
| Geo score, top 50 | precision 1.00 against a base rate of 0.017, lift 59.5x |

Precision 1.00 on the shared exit is what a planted world gives: on real data a shared exit also catches families on one VPN and corporate egress, which is why the lens stays one signal among several and RL-4 stays on. The per-client IP-vs-KYC lens dropped to recall 0.60 of ring members (from 0.74): every ring now logs in through its own exit with less foreign share, and the planted benign mismatchers now include the privacy VPN users and short trips, which a per-client rate test should not flag. Targets were rebased with that diagnosis in `tests/dataplane/test_aml_geo_engine.py`.

**BigQuery Graph** (`src/eios/graph/`). Graph tables are derived from the world's frames, not from the engine's output: accounts, countries, gateways and shared identifiers (devices, payment tokens, IP addresses) as nodes; registered in, logged in via, located in, paid via and uses as edges. They load into `warm_graph` (us-central1, `python -m eios.graph load --project <p>`, 37.5 s `[MEASURED]`) with a `_meta` row naming the world they came from, and `CREATE PROPERTY GRAPH warm_graph.aml_geo` declares the graph. Named queries (`shared_exits`, `account_neighbourhood`) run as GQL through `GRAPH_TABLE`; the SQL around the traversal is shared text, and a DuckDB double runs the same queries as plain joins, so offline, CI and the parity check need no cloud. The store refuses tables built from another world (it caught a mismatched test world on its first run).

GQL runs only on an Enterprise reservation: `eios-graph` in the dev project, baseline 0 slots, autoscale to 50, no project assignment; each graph job names the reservation itself, so nothing else in the project changes how it is billed. Created with `bq mk --reservation --edition=ENTERPRISE --slots=0 --autoscale_max_slots=50 --location=us-central1 eios-graph`; delete with `bq rm --reservation --location=us-central1 eios-graph`. Not yet in Terraform. Cost is bounded by the 50-slot ceiling; an idle reservation costs nothing.

Parity `[MEASURED]` (`python -m eios.graph parity`): BigQuery equals the local double on every query; the graph's shared-exit accounts equal the engine's flags (71 = 71), an independent check from a second derivation; warm latency 1.7 to 1.8 s per query, the first (cold) 9.3 s; 54 to 133 slot-milliseconds per query. A live test (`requires_cloud`) holds the parity.

### N2: geography inside the case
- **Map.** The login view lists shared foreign exits first ("Shared exit in Nigeria: 22 accounts from 8 countries, 67 impossible jumps"), then country pairs. An exit shows who uses it and from where, the hubs set aside under RL-4, and its accounts; picking one draws its users' homes to the exit. Accounts in an exit or a country pair open in one click.
- **Account evidence** (`GET /api/cockpit/geo/accounts/{id}`): registered country, login countries, gateways, impossible jumps with an example (distance and hours), cross-border money with tiers, what each lens concluded, and linked accounts from BigQuery Graph with the source and time ("From BigQuery Graph in 2.1 s"). A graph outage empties only the links and says why; the travel lens without positions is "not assessable", never "none"; an unknown account is a 404.
- **Into the case and back.** "Open the case in the AML workstation" opens that account's dossier, which now carries a Geography card with the same facts and "Open in map". Fixing this exposed a workstation bug: its first load reset the case to the first triage item and ignored the URL's `entityId`, so no forensic deep link opened the account asked for; the URL's entity is now applied after the first load.
- Verified in headless Chrome against the live stack (BigQuery Graph backend): map, exit, account, workstation dossier for `CR11568` (registered in Thailand, 22 of 24 logins from Nigeria through an exit shared by 23 accounts, a jump of 10,041 km in 1.42 h, 24 linked accounts); no console errors.

Open after N2: the reservation is created by CLI, not Terraform; the first graph query of a process takes about 9 s; the workstation's Kinetic Canvas showed "The network for this case could not be loaded" before and after this work (not investigated here).


## J1: official lists and scores in the Jurisdictions view (branch `feat/geo-jurisdiction-lists`)

Why: the map's only list was a secondary summary of the FATF statement, and most countries in the flows were "unrated". Two published sources were added; the Jurisdictions view now colours countries by one basis at a time (FATF, EU, Basel AML), switchable and kept in the address (`?basis=`).

- **EU list of high-risk third countries.** 26 jurisdictions read from the European Commission's page on 2026-10-15 (Delegated Regulation (EU) 2016/1675 as amended to 2026/83; the page has no data file, so the table is transcribed with source and as-of). It differs from FATF `[MEASURED]`: 20 countries on both, 6 only on the EU's list (Afghanistan, Algeria, Namibia, Russia, Trinidad and Tobago, Vanuatu), 5 only on the FATF lists in our table (Bosnia and Herzegovina, Bulgaria, Iraq, Kuwait, Papua New Guinea). The EU follows the FATF with a lag, so showing both is the point.
- **Basel AML Index, Public Edition 2025.** 177 countries scored 0 to 10, bands at the Institute's own breaks (lower below 4.70, medium 4.70 to 6.08, higher above 6.08): 40 higher, 82 medium, 55 lower `[MEASURED]`. The Institute publishes the ranking only inside its report PDF (CC BY-NC-ND 4.0; the data file is a paid edition), so the table was extracted from that PDF and checked against the figures the Institute quotes (Myanmar 8.18 first, Haiti 8.12, Morocco 100th at 5.04, Andorra 171st at 3.48, Finland last at 3.03). Scores are shown as published and never combined into another score. A country outside the public edition (British Virgin Islands, Cayman Islands, Russia, Iran) has no row: "Not in the public index", no fill on the map, never low.
- **Coverage `[MEASURED]`.** The synthetic world's flows touch 17 countries. Before this change 13 of them carried no tier (FATF and offshore centres only). Basel scores 16 of the 17 and the EU list names the remaining one, so none is unrated on every basis. The corridor tiers the engine uses are unchanged on purpose: moving the engine onto the new lists would change the measured lens results, so it is a separate, measured change.
- **Attribution.** The legend says once that the ICIJ counts are not evidence of wrongdoing (P-4); Sources links the EU Commission, the Basel Institute and the ICIJ.
- **Live check found a real bug.** The reader's first query with the new tables failed in BigQuery (`USING (iso2)` became ambiguous after a third join); the fake-client tests could not see it. The `requires_cloud` reader test now covers the new fields and was run against the dev warehouse. Reload with `python -m eios.reference lists --project <id>` (no ICIJ file needed).
- **Deploy note.** The dev warehouse already holds the EU rows in `jurisdiction_risk`; the previous reader query would duplicate those countries, so a deployed reader and its warehouse tables must move together.

## J2: check an address (branch `feat/geo-address-check`)

What: in the Login vs KYC view, one closed line, "Check an IP address". Type an address and get its country and network, and whether the Tor exit list, a cloud provider's published ranges, or the community VPN and datacenter lists name it. It runs on real input; the demo accounts' own gateways are still ones we generated and are not classified by it.

- **Design: a hosted snapshot, not a per-lookup API.** The Tor, cloud and VPN lists have no per-address API, so a snapshot was needed anyway; one code path, no outage dependency, no secret in production (the IPinfo token is used only by the build command), and an investigator's address never goes to a third party. The cost is staleness, shown as an as-of date on every answer; a refresh is one command, `python -m eios.netintel build --project <id>` (token in `EIOS/.env.local`, git-ignored).
- **Build `[MEASURED]`.** IPinfo Lite's 4,167,822 networks merge to 881,614 IPv4 and 1,247,375 IPv6 ranges (adjacent ranges with the same country and network are one; overlaps are refused, there were none). Lists: Tor 1,212, AWS 17,593, Google Cloud 1,127, VPN 11,048, datacenter 44,345 networks. A feed that parses to zero entries stops the build. About 83 s into `warm_reference` (`net_*` tables).
- **Serve `[MEASURED]`.** Lookup is binary search over compact arrays plus a probe per prefix length for the nested lists: 14 µs per address. The snapshot loads in the API's start-up background in 15 s; the arrays hold 60 MB, and the API process went from 335 MB to 473 MB resident with it loaded, inside the service's 1 GiB. It is not part of readiness.
- **Findings along the way.** The first load took 210 s: the DataFrame read needed a package the project does not have, so every table fell back to the slow REST path. Arrow plus the BigQuery Storage API fixed it (15 s). `rows` is a reserved word in BigQuery, so the meta column is `row_count`. A test now compares every loaded table's columns with its declared schema, because the fake warehouse ignores schemas and the real one does not.
- **Honesty.** "Not on any list we hold" always carries "that does not mean the address is clean". The X4BNet VPN and datacenter lists hold only IPv4 networks, so an IPv6 verdict says those lists "cannot rule this address out" (computed from the data, not hard-coded). The country is where the address is registered, which a VPN can hide, and it says so. Private and reserved addresses are not looked up. The community lists over-match: 8.8.8.8 is "on a datacenter list" because Google's resolver sits in a hosting network.
- **Privacy.** The route is a POST (the address is not in a URL or an access log), nothing on the path logs it (a test fails if it does), and the panel says it is not stored.
- **Attribution.** IPinfo Lite is CC BY-SA 4.0 and asks for "IP address data is powered by IPinfo" with a link, shown under Sources. X4BNet is MIT.
- **Deploy note.** Build the snapshot into the prod-like `warm_reference` before a deploy that includes this (`--project eios-hackathon-prod`); until then the check answers a plain 503 "no network data loaded here". Nothing is deployed.

## G1: the geo assistant (branch `feat/geo-agent`)

Supersedes M5 above. Design, measured results and known limits are in `docs/geo-agent.md`. In short: a sixth workstation (`geospatial`) with seven geo capabilities, an Ask panel beside the map that moves the map only to objects a tool returned in the same turn (Back undoes a move), a list-edition comparison in the Jurisdictions view (what an FATF plenary or an EU amendment changes for this book), two new BigQuery Graph queries (`exit_ring`, `country_links`) at parity with the local double, and "Verify figures", which derives every figure of an answer again through the governed port. Offline baseline 116 of 116 `[MEASURED]`; live, four of four questions assembled on one model call in 3.0 to 4.5 s `[MEASURED]` after two fixes the first live run called for. The N3 evidence bundle is not started. Nothing is deployed.

## G0 to G3, and the GEOG 850 additions (branch `feat/geo-g2`)

Gates first, then the loop the investigator works in. Each exit gate is a measurement, listed in `docs/geo-agent.md` ("Measured"); a gate that failed once is recorded with what changed.

| Phase | Exit gate | Result `[MEASURED]` |
|---|---|---|
| G0 gates | a stub that always answers "42" fails the geo cases | fails 22 of 22 |
| G1 assistant | every figure traced to a tool; live turns within budget | 22 of 22 live, 100.0% supported, median 2.3 s, p95 4.1 s, no timeouts |
| G2 case loop | an approved hold names the exact evidence; the evidence replays | tested end to end: seal, stage, signed refs, two approvers, replay equal |
| G3 list change | two list editions compared for the book in under 200 ms | median 26 to 35 ms, p95 at most 48 ms |

What the plan added, from the GEOG 850 workflow (<https://courses.ems.psu.edu/geog850/node/338>):
- **U8 login hotspots**, built. Countries that foreign accounts keep returning to, tested against chance with false discovery control and RL-4; the six planted ring-exit countries, precision and recall 1.00, on the served world and five unseen seeds. A first version counted repeat sessions and flagged two travel destinations (precision 0.75); counting accounts once fixed it.
- **False-lead control**, built. Benign readings for an account (a shared exit, a hub, one country abroad, no money abroad); "could be chance" for a tested country that is not listed; a refusal to rank people by origin.
- **U9 "where else"**, measured, not built: the shared-exit rule already finds every planted exit and nothing below it is enriched (`docs/geo-agent.md`, Known limits).
- **U4 corridor change, U7 teleconnection**, deferred until a world plants a temporal pattern to be found.
- Colocation window, skipped: shared-exit precision is already 1.00.

Nothing is deployed.
