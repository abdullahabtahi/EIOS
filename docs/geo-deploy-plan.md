# Geo deploy plan (plan only, nothing applied)

Status: for the owner's decision. Nothing here has been run against `eios-hackathon-prod`; every step that changes the cloud needs your explicit go. Read-only facts below were checked on 2026-10-16.

## What the prod-like project has today

| Piece | Dev (`eios-hackathon`) | Prod-like (`eios-hackathon-prod`) |
|---|---|---|
| Warm history datasets (`warm_aml`, `warm_partner`, ...) | yes | yes (Terraform, `bigquery_warm`) |
| `warm_reference` (FATF, EU and Basel lists, ICIJ, address-check snapshot) | yes | **absent** |
| `warm_graph` and the `eios-graph` reservation | yes | **absent** |
| Geo assistant, evidence bundles, hotspots in the image | n/a | **not deployed** (merged to `main` only) |
| Google Maps key in the web build | local `.env.local` | **not wired**: the web Dockerfile and `cloudbuild.cockpit.yaml` pass only the Firebase and API values, so the deployed map would read "No Google Maps key is configured" |

`warm_reference` and `warm_graph` are not in the `bigquery_warm` Terraform module (it manages the contract-driven history datasets); the loaders create them, so the API identity has no read grant on them either.

## Steps, in order

1. **Terraform (targeted plan, shown to you first):** add `warm_reference` to the warm module's datasets, with a reader grant for the API identity and a writer grant for whoever loads it. Run `terraform plan -target=module.bigquery_warm` and show the output; apply only on your go.
2. **Load the reference layer** into prod: `python -m eios.reference build --project eios-hackathon-prod --icij-entities <nodes-entities.csv> --icij-as-of <date>` (the ICIJ file is a manual download; `lists` alone reloads only the FATF, EU and Basel lists), then `python -m eios.netintel build --project eios-hackathon-prod` (needs a free IPinfo token or a downloaded `ipinfo_lite.csv.gz`).
3. **Maps key:** create a browser key limited to the Maps JavaScript API and to the demo URL as HTTP referrer; add `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` as a build arg in the web Dockerfile and a `_MAPS_API_KEY` substitution in `cloudbuild.cockpit.yaml`. Verify, as the runbook says, by grepping the built `/_next/static` chunks for the key.
4. **Build and deploy** the API and web images by digest as `pipeline@`, through the runbook (`docs/runbooks/cockpit-deploy.md`), after the prod-only prerequisites on that page (Model Armor templates, the Enterprise flag) are confirmed.
5. **Verify on the live revision** (below), then decide on the graph backend.

## Decisions for you

- **D1. Graph backend in prod.** The local double gives the same answers (parity measured against BigQuery Graph on every named query) and costs nothing; BigQuery Graph needs the `warm_graph` load and the `eios-graph` reservation (created by CLI, Enterprise edition, autoscale from a baseline of 0). My recommendation: deploy first on the local double, then switch on BigQuery Graph as its own small change (three env vars plus the reservation), so the first deploy has one risk fewer. Pick BigQuery Graph first only if the demo has to say "BigQuery Graph" on day one.
- **D2. Reviewer exposure.** The shared judge accounts are public by design. Geo adds no new write path (a hold is still staged and approved through the intent hub), but I have not checked which roles the judge accounts hold, so whether they can stage a hold is unconfirmed. Confirm it before the deploy; keep four-eyes (the proposer cannot approve) and the verify and copilot rate limits as they are.
- **D3. Data labelling.** Nothing on screen says the data is synthetic (UI decision of 2026-10-14). The demo has to say it out loud.

## Verify after deploy

- The geospatial tab loads the map (no key message) and "Login vs KYC" lists the six shared exits.
- An Ask turn about hotspots returns six countries and does not list the Netherlands; a nationality question is refused with no tool call.
- A hold proposal shows a bundle id; replay reports every figure equal; a proposer cannot approve their own hold.
- The address check answers (not a 503 "no network data loaded here").

## Rollback

Traffic back to the previous Cloud Run revision (images deploy by digest). The new datasets are additive; nothing existing is altered, so they can stay.

## Cost and risk

Small. The warm loads are a few tables; a graph job measured 191 slot-milliseconds `[MEASURED]`; model calls are the same fast-model turns as today. The risks are the missing Maps key (visible and cheap to fix) and the first graph job's cold start (about 10 to 12 s, run it once before a demo).
