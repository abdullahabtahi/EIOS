# Geo agent: geography as evidence inside the investigation

Status: the assistant is merged (#95); the quality gates, evidence bundles and login hotspots are on `feat/geo-g2`. Product direction: `docs/financial_geospatial.md`. Earlier geo work: `docs/geospatial-milestones.md` (M0 to N2, J1, J2, G1 to G3).

## What it is

An ADK assistant for the Geospatial tab, the sixth workstation (`geospatial`). It answers "why is this suspicious and who else is involved", moves the map to what it found, and can propose a hold that a second person approves. It reads only governed tools; every figure it writes is matched to a value a tool returned in the same turn, and every map move names an object a tool returned in the same turn.

Lead persona: the investigator (shared exits, accounts, corridors). The MLRO gets one capability of their own: what a change of a published list (an FATF plenary, an EU amendment) changes for this book.

## Shape

```
Geospatial tab ── question + map context (view, basis, selection) ──▶ POST /api/cockpit/copilot/query (role geospatial)
     ▲                                                                     │
     │ answer + figures with sources + view_commands                       ▼
     │                                   ADK LoopAgent: prefetch ─▶ drafter (Gemini) ─▶ assembler
     └── the map applies a command                │ governed tool port only (no model-written SQL or GQL)
         as a URL change (Back undoes it)          ▼
                  geo engine · BigQuery Graph (named GQL, DuckDB double) · reference lists · intent hub
```

- **Its own workstation, not more tools on the AML one.** The AML investigator already holds the ceiling of 13 tools; more tools there would worsen its tool choice. The geospatial workstation holds the seven geo capabilities plus the account dossier, the hold proposal, the SAR draft and regulation search (11).
- **Map commands are placeholders, like figures.** The drafter writes `{{map:<kind>:<id>}}`; the assembler accepts it only when a tool of this turn listed that object in its `map_targets`, strips it from the text and returns it as a `view_command`. A command for anything else sends the draft back, exactly like a figure no tool returned. More valid moves than the map follows (three) are cut to the first three rather than rejected: the limit is presentation, not proof, and a live run showed the redraft after such a rejection can collapse into a refusal. No extra model round trip, unlike a frontend tool call (the CARTO pattern), and no model-written coordinates or layer JSON.
- **Prefetch from the map.** What is selected on the map decides the first tool (an exit, an account, a corridor, a country, or the overview), run by the platform before the model's first call, so a typical question needs one model call.
- **BigQuery Graph where a join is a traversal.** Three named queries: `account_neighbourhood` (N2), `exit_ring` (the users of a shared exit, then the accounts sharing a device, payment token or address with them) and `country_links` (accounts one hop from those registered in, paying through or logging in from a country). Hubs (RL-4) never link anyone.

## Capabilities

| Capability | Tool | What it returns |
|---|---|---|
| `geo.overview` | `get_geo_overview` | Each lens: how many it flags, how many it can judge at all; the top shared exits and elevated corridors; the login hotspots and how many countries were tested |
| `geo.leads` | `list_geo_leads` | Ranked shared exits, corridors, login-country pairs or accounts, in the map's order |
| `geo.exit` | `get_shared_exit` | Who uses an exit and from where, the ring around it from BigQuery Graph, the rule it met |
| `geo.corridor` | `get_corridor` | Volume, accounts and events on a corridor, both ends' standing on each list |
| `geo.account` | `get_geo_account` | One account's geography (N2 evidence) with the rule behind each lens conclusion, and the innocent readings the data supports (a shared exit, a hub, one country abroad, no money abroad) |
| `geo.jurisdiction` | `get_jurisdiction` | FATF, EU and Basel standing with source and as-of, and this book's exposure to the country |
| `geo.list_change` | `get_list_change_impact` | What a list change does to this book: countries added and removed, accounts, sessions, payments and graph links |

## Honesty rules carried over

A lens that cannot judge an account says "not assessable", never clean. A country absent from the Basel public edition is unrated. A graph outage empties only the graph section and says why. The instructions forbid a conclusion from a country of residence alone: geography is one signal among several.

Three more rules live in the instructions and are covered by golden cases: a hotspot lens that tests a country and does not list it says "could be chance", never clean; a SAR paragraph quotes Malta's duty to report by sentence number from the regulation index (the licensing jurisdiction), never from memory; an answer runs data, then what it means, then the next step, and names the innocent readings before a conclusion.

**People are never judged by origin.** A question that asks to rank or judge people by nationality, ethnicity, race or religion is refused by a callback before the drafter's model call (no model, no tools): geography here is evidence about behaviour, never about who someone is. The refusal is marked so the turn counts no model call.

**Numbers in words are figures.** "Two countries" is checked like "2 countries": the assembler parses spelled numbers (units, tens, scales, "and") and requires a returned value. The first live run showed the model counting list items itself and writing the count in words; the tools now return those counts (`lens_count`, `login_country_count`, `gateway_count`).

## Evidence bundles (G2)

A turn that proposes a hold or drafts a SAR seals its evidence: the question, the answer and every tool result, as canonical JSON identified by its SHA-256 (`src/eios/evidence/`). The bundle is write-once in the record store (Firestore when deployed, memory in dev); reading it re-hashes it and a mismatch is refused as tampered.

- **Staging names the evidence.** `evidence_bundle_id` rides on the stage request; the gateway refuses an unknown bundle or one about another entity (422) and a tampered one (409). The id is added to the Action Intent's `evidence_refs`, so the KMS signature covers it and the approved decision names exactly what it rested on.
- **Four eyes unchanged.** The proposer cannot approve; two other people do (`PENDING_SECOND_EYE`, then `COMMITTED`). `tests/cockpit/test_evidence_loop.py` runs the whole loop with a scripted turn.
- **Replay.** `POST /api/cockpit/evidence/{id}/replay` re-derives every figure through the governed port as the caller and reports equal, differs, failed or not replayed per call. A changed figure shows as a difference. It has the verify rate limit. The Ask panel shows the bundle and a Replay button; an unreadable reply reads "Nothing was verified".

## Login hotspots (U8)

Countries that foreign accounts keep returning to, tested against chance (`src/eios/dataplane/aml_geo_hotspots.py`), after the warning in GEOG 850 that density clustering finds patterns in noise. Per login country: foreign accounts, and of those the ones with two or more logins (returning). A one-sided binomial test against the book's median returning share, Benjamini-Hochberg at 5% false discovery. Hub gateways are set aside first (RL-4). A count map ranks the Netherlands first (a commercial VPN); this lens does not list it.

## Verify figures

Under an assembled answer, "Verify figures" sends each cited figure's fact id and shown value to `POST /api/cockpit/copilot/verify`. The backend derives every figure again through the same governed port, as the same operator and workstation, and reports how many match. A figure that cannot be derived again (refused, gone, not a figure) is never a match. An outage, or a reply without its counts and rows, reads "Nothing was verified". The route calls each result once however many figures it holds (`FactResolver.resolve_many`), so six figures from one exit are one graph job, not six. It has its own rate limit (`EIOS_RATE_VERIFY_PER_USER`, default 30 a minute and 900 a day `[ASSUMPTION]`), so checking an answer does not spend the operator's questions.

Which fact a plain figure cites when several returned facts share its value: the words written right after the number choose (the fact's unit counts twice, a word of its own name once); with nothing to choose by, the first returned fact is cited, as before.

## Measured (local gateway, dev project, 2026-10-16)

| What | Result `[MEASURED]` |
|---|---|
| Offline ADK baseline, dev and validation splits (scripted model) | 116 of 116 turns pass, 0 inconclusive; 11 geo cases, 3 repeats each |
| BigQuery Graph parity, every named query including `exit_ring` and `country_links` | equal to the DuckDB double; median 1.70 s, max 5.19 s (the first query of the process) |
| `country_links` over 13 countries | 1.56 s, 191 slot-milliseconds |
| Live turns on the fast model, first run (six questions) | three good (EU delisting, account geography, a nationality question refused); three failed (exit ring, FATF plenary, SAR paragraph) |
| Live turns after the two fixes (exit ring, FATF plenary, account geography, SAR paragraph) | four of four assembled, one model call each, 3.0 to 4.5 s wall; the map moved to returned objects only (three, two, three and three moves) |
| Verify, six exit figures from a live answer | six of six match; 10.2 s calling once per figure, 1.6 to 2.0 s warm calling once per result; 12.5 s on the first call after a restart (the cold graph job) |

Quality gates over the 11 geo golden cases (`feat/geo-g2`, `docs/geospatial-milestones.md` G0 to G3):

| What | Result `[MEASURED]` |
|---|---|
| G0: a stub that always answers "42" | fails 22 of 22 turns, so the gates can tell a broken agent from a working one |
| G1: live, fast model, 22 turns, run `g1_live4` | 22 pass, 0 fail; 100.0% of figures supported; median 2.3 s, p95 4.1 s, no timeouts; every turn found data (0 of 22 starved) |
| Earlier live run (`g1_live3`, before the origin guard and the ranking prefetch) | 20 of 22; the two misses were a ranking question and a nationality question, both fixed |
| G3: comparing two list editions for the book | median 26 to 35 ms, p95 at most 48 ms (limit 200 ms) with the local graph |
| Login hotspots, six ring-exit countries planted | 6 hotspots of 46 countries tested; precision 1.00, recall 1.00; the same on five unseen world seeds; 8 ms. Without RL-4 the VPN country is a seventh (precision 0.86) |
| Evidence loop | a scripted hold turn: seal, stage, signed refs verified, the proposer refused, two approvals commit, replay equal; a changed figure replays as a difference |

What the live runs found, and what changed:
- **The first live run measured nothing.** On the fixture plane every tool answered "no data" and the turns still passed. The adapter now loads the geo test data for live runs, and the report counts the turns where every tool found no data. (Making such a turn inconclusive broke legitimate no-data cases, so it is a reported line, not a verdict.)
- **A count in words slipped past RL-1.** "Two countries" was the model counting a list. The assembler now checks spelled numbers and the tools return the counts.
- **"$0" bound to the wrong field.** The scorer took the 0 inside "$0" as a count; a figure now binds only where it is written whole.
- **Nationality questions** are refused before the model (above).

What the first live run found, and what changed:
- **Too many map moves.** The model wrote seven valid moves; the assembler rejected the draft for exceeding three, and the redraft said it could not answer. Fixed by keeping the first three.
- **A true figure cited to the wrong fact.** "3 impossible jumps" was cited to `gateways[1].accounts`, which also equalled 3; "22 foreign logins" to `exit_sessions`. Fixed by the attribution rule above; the tests for it fail on the old assembler.

## Known limits

- **A sibling with the same value and unit.** "Logins from Nigeria (22 sessions)" cites `exit_sessions` (22 sessions) rather than Nigeria's row of `login_countries`: same value, same unit, and the words that tell them apart ("Nigeria") come before the number while fact ids carry no country name. The figure is right; its citation is a sibling.
- **The first graph job of a process** takes about 9 to 12 s; later ones about 1.6 to 2 s.
- **The `eios-graph` reservation** is created by CLI, not Terraform.
- **The evidence bundle freezes the tool results the turn saw, not a BigQuery snapshot.** Replay asks the governed port again, so a later change in the data shows as a difference rather than being frozen out. A time-travel snapshot of the graph tables would pin it; not built.
- **Measured and not built: "where else" (U9).** The idea was to rank other gateways by their likeness to a confirmed ring exit. On the served world every ring exit already passes the shared-exit rule (precision and recall 1.00), and the gateways just below it carry no planted ring members beyond chance: of 1,362 gateways with one foreign account, 5 held a ring member, and of 47 with two, one did; none held two `[MEASURED]`. A ranker would have nothing to find that the rule misses, so it was not built. It becomes worth building when a world plants a sub-threshold ring.
- **Deferred: corridor change over time (U4) and places whose money moves together (U7).** Nothing temporal is planted in the world, so a detector could not be judged on false alarms against power. Build them together with an injected pattern, so the evaluation has a truth to find.
- **Sealed held-out case (`geo_eu_delisting`), run once live on 2026-10-16 after the owner's go:** passes (one turn, one model call, 2.6 s `[MEASURED]`). The seal is spent: a further change judged by it would be fitting to it.
- **A failed turn is closed in its thread.** A timeout or outage used to leave the operator's question unanswered, and the next reply summarised both. The thread now records the plain "can't answer right now" reply, so the next turn answers only its own question (`tests/assistant/test_runtime.py`).
- **Deploy** needs the reference and network data loaded into the prod-like warehouse first, and explicit approval. Nothing here is deployed.
