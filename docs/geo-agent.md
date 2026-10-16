# Geo agent: geography as evidence inside the investigation

Status: built on `feat/geo-agent`. Product direction: `docs/financial_geospatial.md`. Earlier geo work: `docs/geospatial-milestones.md` (M0 to N2, J1, J2).

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
| `geo.overview` | `get_geo_overview` | Each lens: how many it flags, how many it can judge at all; the top shared exits and elevated corridors |
| `geo.leads` | `list_geo_leads` | Ranked shared exits, corridors, login-country pairs or accounts, in the map's order |
| `geo.exit` | `get_shared_exit` | Who uses an exit and from where, the ring around it from BigQuery Graph, the rule it met |
| `geo.corridor` | `get_corridor` | Volume, accounts and events on a corridor, both ends' standing on each list |
| `geo.account` | `get_geo_account` | One account's geography (N2 evidence) with the rule behind each lens conclusion |
| `geo.jurisdiction` | `get_jurisdiction` | FATF, EU and Basel standing with source and as-of, and this book's exposure to the country |
| `geo.list_change` | `get_list_change_impact` | What a list change does to this book: countries added and removed, accounts, sessions, payments and graph links |

## Honesty rules carried over

A lens that cannot judge an account says "not assessable", never clean. A country absent from the Basel public edition is unrated. A graph outage empties only the graph section and says why. The instructions forbid a conclusion from a country of residence alone: geography is one signal among several.

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

What the first live run found, and what changed:
- **Too many map moves.** The model wrote seven valid moves; the assembler rejected the draft for exceeding three, and the redraft said it could not answer. Fixed by keeping the first three.
- **A true figure cited to the wrong fact.** "3 impossible jumps" was cited to `gateways[1].accounts`, which also equalled 3; "22 foreign logins" to `exit_sessions`. Fixed by the attribution rule above; the tests for it fail on the old assembler.

## Known limits

- **A sibling with the same value and unit.** "Logins from Nigeria (22 sessions)" cites `exit_sessions` (22 sessions) rather than Nigeria's row of `login_countries`: same value, same unit, and the words that tell them apart ("Nigeria") come before the number while fact ids carry no country name. The figure is right; its citation is a sibling.
- **The first graph job of a process** takes about 9 to 12 s; later ones about 1.6 to 2 s.
- **The `eios-graph` reservation** is created by CLI, not Terraform.
- **Not built from N3:** the evidence bundle that freezes a decision's inputs on BigQuery snapshots. The SAR geography paragraph and the hold proposal from the map are in.
- **Not run:** a live baseline over all geo golden cases, and the sealed held-out case (`geo_eu_delisting`); both wait for the owner's go.
- **Deploy** needs the reference and network data loaded into the prod-like warehouse first, and explicit approval. Nothing here is deployed.
