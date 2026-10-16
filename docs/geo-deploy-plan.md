# Geo deploy plan (plan only, nothing applied)

Status: the code and Terraform are written and the Terraform plan has been run; nothing has been applied. Every step that changes the cloud needs the owner's explicit go. Read-only facts below were checked on 2026-10-16.

## What the prod-like project had, and what changes

| Piece | Prod-like before | After this change (still to be applied) |
|---|---|---|
| `warm_reference` (FATF, EU, Basel lists, address check) | absent | dataset, labelled, API read grant, loader grant for `warm_writer_members` |
| `warm_graph` and the Enterprise reservation | absent | dataset, and reservation `eios-graph`: baseline 0, autoscale cap 50 slots (the smallest BigQuery allows; it must be a multiple of 50) |
| Graph backend | none | BigQuery Graph, with a result cache and a fall-back to the local double (the result's source says which answered) |
| Regulation text (Agent Search) | **not configured** (no `EIOS_KNOWLEDGE_DATA_STORE` on the live revision, so the SAR duty and every regulation question answer "no index") | reads the dev data store: `EIOS_KNOWLEDGE_DATA_STORE`, `EIOS_KNOWLEDGE_PROJECT`, and `roles/discoveryengine.viewer` for the API identity on that project |
| Prepared briefs | not deployed | `EIOS_AMBIENT_TOP_N=5`; a fresh brief is not rebuilt, so scaling out does not repeat the model calls |
| Google Maps key in the web build | **not wired** (the map would read "No Google Maps key is configured") | still to do: a build argument and a referrer-restricted key from the owner |

## Decisions (owner, 2026-10-16)

- **D1. BigQuery Graph in prod from the start**, with the cost and availability guards below. The reasons: it is the Google-native graph feature the geo story names, parity with the local double is measured on every named query, and for a one-month demo the cost is small (the largest graph job used 191 slot-milliseconds `[MEASURED]`).
- **D2. Judge accounts** are one analyst and two approvers (`tools/seed_demo_operators.py`), so the analyst can stage a hold and the two approvers can approve it: four-eyes can be shown live on the deployed site, with the proposer unable to approve. Keep the verify and copilot rate limits.
- **D3. Regulation index read from the dev project** (no second data store to pay for); the corpus is public regulation text.
- **D4. Data labelling.** Nothing on screen says the data is synthetic (UI decision of 2026-10-14). The demo has to say it out loud.

## Cost and availability guards (checked against Google's docs)

- **Capacity billing, bounded.** GQL needs an Enterprise reservation, billed in slots. Baseline 0 means an idle reservation costs nothing; the autoscale cap (`graph_max_slots`, 50, the minimum allowed) bounds the worst case. Bytes-billed limits and custom daily quotas apply only to on-demand pricing, so the cap is the control, not those. The docs recommend a non-zero baseline for predictable speed; at baseline 0 the first job is slow, so the API warms the graph at start-up.
- **Every graph job is labelled** (`app=eios`, `component=geo`, `query=<name>`) **and has a 30 s timeout**, so a stuck job is stopped and graph slot use filters on its own in billing. Reservation labels filter only the slot-usage SKU, not the reservation fee.
- **Repeated questions are cached** (256 entries, copies returned, failures never cached).
- **Fall-back, not silence.** If the warehouse is unreachable the local double answers and the figure's source reads `graph.local`, not `graph.bigquery`. A refused query stays refused.
- **Budget alert.** `budget_alerts` is already in the prod-like Terraform (USD 2,000 a month with alerts at 50, 80 and 100 percent `[ASSUMPTION]`); I could not confirm it is applied, because reading budgets needs an API that is not enabled. For a demo this size a lower figure would catch a runaway sooner: consider lowering it.
- **Not done:** billing export to BigQuery (the checklist's visibility item; it needs a dataset and the owner's go) and Terraform labels on the reservation (the resource does not take them).

## The Terraform plan (read-only, `terraform plan` with targets)

`12 to add, 1 to change, 0 to destroy`:
- add: datasets `warm_reference` and `warm_graph` with API read and owner write grants; reservation `eios-graph` (Enterprise, baseline 0, max 50); custom role `eiosGraphReservationUser` (only `bigquery.reservations.use`) and its grant to the API identity; `roles/discoveryengine.viewer` for the API identity in the dev project.
- change: the `eios-api` Cloud Run service gets six new variables (`EIOS_AMBIENT_TOP_N`, `EIOS_GRAPH_BACKEND`, `EIOS_GRAPH_PROJECT`, `EIOS_GRAPH_RESERVATION`, `EIOS_KNOWLEDGE_DATA_STORE`, `EIOS_KNOWLEDGE_PROJECT`).
- **Also in the plan, not mine:** enabling `cloudtrace.googleapis.com` and `telemetry.googleapis.com`, and the variables `EIOS_TRACE_EXPORT=cloud_trace` and `EIOS_SERVICE_NAME`. They belong to the Cloud Trace work merged earlier (#89 to #91) and never applied. Applying the service target deploys them too. Decide whether to include them or to apply the geo resources first.

## Steps, in order (each cloud step needs the owner's go)

1. Apply the targeted plan above (the owner reads it first).
2. Load the data, with the owner's credentials: `python -m eios.reference lists --project <prod>` (add `build --icij-entities ...` for the offshore counts, a manual download), `python -m eios.netintel build --project <prod>` (an IPinfo token or file), and the graph tables through `python -m eios.graph`.
3. Maps key: the owner creates a browser key limited to the Maps JavaScript API and the demo URL as HTTP referrer; add `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` as a build argument in the web Dockerfile and a `_MAPS_API_KEY` substitution in `cloudbuild.cockpit.yaml`.
4. Build the API and web images by digest as `pipeline@` (the private README holds the exact commands), then deploy through a targeted plan.
5. Verify (below), then teardown at the end of the review.

## Verify after deploy

- The geospatial tab loads the map (no key message) and "Login vs KYC" lists the six shared exits.
- An Ask turn about hotspots returns six countries and does not list the Netherlands; a nationality question is refused with no tool call.
- A SAR question quotes Malta's duty by sentence number (the regulation index works).
- A hold proposal shows a bundle id; replay reports every figure equal; the proposer cannot approve; two approvers can.
- The address check answers (not a 503 "no network data loaded here").
- An exit's ring shows `graph.bigquery` as its source, and a second identical question returns faster (the cache).
- The AML dossier column shows a "Prepared brief" for a top alert.

## Rollback and teardown

Traffic back to the previous Cloud Run revision (images deploy by digest); the new datasets are additive. At the end of the review: delete the reservation (`eios-graph`), drop `ambient_top_n` to 0, take down the reviewer accounts and the public login card, and remove the dev-project viewer grant if the prod API no longer reads that data store.
