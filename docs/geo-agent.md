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
- **Map commands are placeholders, like figures.** The drafter writes `{{map:<kind>:<id>}}`; the assembler accepts it only when a tool of this turn listed that object in its `map_targets`, strips it from the text and returns it as a `view_command`. A command for anything else sends the draft back, exactly like a figure no tool returned. No extra model round trip, unlike a frontend tool call (the CARTO pattern), and no model-written coordinates or layer JSON.
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
