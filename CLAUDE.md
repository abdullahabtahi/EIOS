# CLAUDE.md

Guidance for Claude Code in this repository. Keep it short; link, don't copy. If a fact is in the code or a doc, point to it.

## 1. Orientation

Forward Deployed Engineering (FDE) engagement, POC to production, for the **Enterprise Intelligence Operating System (EIOS)**. Client persona is Deriv (briefs in `docs/brief/`). `EIOS/` is the production root: Python backend (`uv`, Python 3.14) and the Next.js cockpit in `EIOS/web-prototype/` (its own `CLAUDE.md` holds UI rules and the persona/workstation matrix). `specs/` holds the numbered feature specs up to 032 (historical contracts, read before changing what they describe); newer work is a short `docs/*.md` note plus the PR text.

Read the doc for the area you touch, not all of them:

| Area | Doc |
|---|---|
| ADK migration status and decisions | `docs/adk.md`, `docs/adk-research.md` |
| Agent jobs, tool catalogue, topology | `docs/agent-architecture.md` |
| Measured "before" picture of the copilot | `docs/agent-baseline.md` |
| First measured workflow, metrics M1-M6 | `docs/lighthouse.md` |
| Data platform, warm tier, DDD contexts | `docs/data-strategy.md` |
| Regulation retrieval (Agent Search, quotes, ingestion, eval) | `docs/knowledge-retrieval.md` |
| Executive plane (fitted causal graph, backtested forecast, what-if) | `docs/executive-engine.md` |
| Operations plane (ingestion replay, probes, red lines, restore drill) | `docs/operations-engine.md` |
| Geo/AML product direction | `docs/financial_geospatial.md` (v3 draft) |
| Geo assistant (sixth workstation, map moves, verify figures), geo milestones | `docs/geo-agent.md`, `docs/geospatial-milestones.md` |
| Prepared briefs for the top alerts (ambient dossiers) | `docs/ambient-dossiers.md` |
| Deploy, environments, exceptions | `docs/runbooks/cockpit-deploy.md`, `EIOS/docs/environments.md` |

## 2. Commands

Backend, from `EIOS/`:
- `make setup`, `make test` (`-n auto`), `make lint`, `make types` (strict mypy), `make check` (all PR gates, same `config/gates.yaml` as `.github/workflows/pr.yml`, reports in `evals/reports/`)
- One test: `uv run pytest tests/cockpit/test_server_gateway.py::test_name -q`
- Network/cloud tests are off by default: `EIOS_TEST_NETWORK=1` (markers `requires_network`, `requires_emulator`, `requires_cloud`)
- Gateway / Backend: `PYTHONPATH=src uv run uvicorn eios.api.app:app --host 127.0.0.1 --port 8002` (mounts all domain routers + cockpit gateway; do not run `eios.cockpit.server:app` directly as domain APIs will 404). The assistant also needs `GOOGLE_GENAI_USE_VERTEXAI=1` and the GCP vars in section 6, else every copilot query is a 503.
- Agent quality gates (spec 022; code `src/eios/agent_gates/`, cases `evals/golden/`, suites `evals/agent/`), run with `PYTHONPATH=src:.`:
  - Baseline offline: `python -m evals.agent.baseline --runtime adk` (scripted model, free; splits `dev,validation` by default, `--split sealed` only to judge a finished change, `docs/agent-eval-splits.md`). Do not run live or multi-repeat evals unless the user asks.
  - Live (spends money, needs `EIOS_AGENT_EVAL_MAX_TURNS` and the GCP vars in section 6): add `--live --repeats 1 --out evals/reports/agent_baseline_live`
  - Re-grade a saved run with no model call: `--runtime recorded --records <records.jsonl>`
  - Faithfulness over stored turns: `python -m evals.agent.faithfulness_suite --records evals/recorded --twice`
  - Retrieval eval: `python -m evals.knowledge.run`

Web, from `EIOS/web-prototype/`: `npm run dev|build` (both `--webpack`), `npm run lint`, `npm test` (vitest; one file: `npx vitest run <path>`), `npx tsc --noEmit` must be 0 errors.

## 3. Architecture

Layers consume the one below only through contracts:
- **L0 `foundry/`**: seeded synthetic generators and the planted-truth worlds in `foundry/scenarios` (AML, partner, executive). All current data is synthetic; the truth tables are read by evaluations only, never by an engine.
- **L1 `ingestion/`, `contracts/`**: Pub/Sub, contract validation (breach goes to DLQ, never dropped), DuckDB hot state with Parquet warm start.
- **L2 `ontology/`**: `metrics/` registry (ADR-003), `graph/` with CGNAT hub suppression (ADR-004), `omcp/port/` the typed tool port the assistant calls (the name-dispatched `omcp/server.py` is not on the agent path), `actions/` Action Intents (`intent_hub.py` validates, signs, ledgers; `signer.py` is Cloud KMS when deployed, local-dev only in dev/test), `auditor/` the Metric Auditor Gate.
- **L3 `assistant/`**: the ADK assistant (ADR-019, spec 021) is the only copilot runtime. One agent per workstation over the governed tool port, a drafter and an assembler that shows a figure only if a tool returned it in the same turn: the drafter writes figures plainly ("61.67%", "$1.09M") and the assembler matches each to a returned value at the precision and in the unit written, citing it; `{{fact:id}}` placeholders are still accepted, and a figure no tool returned is rejected (one redraft, then fail closed; `EIOS_ASSISTANT_PLAIN_FIGURES=0` restores placeholder-only). Regulation text is quoted by sentence number from the tool result (`{{quote:...}}`), never typed. ADK Firestore sessions, Model Armor screening, a 30 s turn deadline. An outage is a plain 503 `offline`; there is no replay and no legacy fallback. `cockpit/assistant_gateway.py` builds it; `llm_gateway/` is provider-neutral and the assistant reaches Google types through `llm_gateway/providers/adk_types.py`. `knowledge/` is the regulation index behind a seam (Agent Search live, a static double offline).
- **Domain modules** (`aml/`, `churn/`, `fraud/`, `synthesis/`) produce the numbers L3 narrates.
- **L4 `cockpit/`**: `server.py` FastAPI gateway; `governance_runtime.py` assembles signer, ledger, hub and WORM from env; `auth.py` verifies Firebase tokens (analyst, approver, compliance_head). `eios.api.app` mounts the cockpit and domain routers and is what the container runs.

**Data plane (`dataplane/`):** `EIOS_DATA_PLANE=engine` (the default outside tests) runs the real engines over seeded worlds, and the cockpit server, the API routers and the assistant share one `ReadModels` from `dataplane.plane.read_models()`; `fixture` keeps the hand-written services and is what unit tests use. AML, partner, executive and operations are engine-backed (origin `engine`); compliance reads the governance runtime's real ledger (origin `live`). Each plane is checked against what its world planted and the result is logged as `[MEASURED]` at build.

Known gap: `api-bridge.ts` still falls back to a labelled AML graph replay (refused for engine cases) when the backend is down, so a working UI does not prove backend wiring. The copilot has no client-side fallback.

Process gates: add gates as rows in `config/gates.yaml`, never as runner edits. Quarantined gates (`config/quarantine.yaml`) fail the run after `expires`. The lint gate also runs `tools.repo_checks` (file size, forbidden literals, frozen models, pinned dependencies, no tracked plan/state/key files). `adr_check` needs `docs/evidence/adrs/` to agree with the index in `docs/spikes_and_adrs.md`.

## 4. Constitutional invariants (non-negotiable)

1. **No LLM-computed metrics (RL-1).** Every number comes from a deterministic engine (DuckDB semantic engine, BigQuery job, Flink). The LLM synthesises and explains.
2. **No autonomous write-back (RL-2).** Agents propose only. Any state change needs a Cloud KMS-signed (ECDSA P-256), expiring Action Intent approved by a human under four-eyes.
3. **Honest uncertainty (RL-3).** A causal claim shows as causal only if the placebo refuter p > 0.05 and confidence >= 0.80; otherwise "Correlation Only". The refuters cannot see confounding: the adjustment set is a domain input.
4. **CGNAT hub suppression (RL-4).** Shared-IP nodes with degree > 100 are collapsed out of laundering rings.
5. **WORM decision ledger (RL-5).** Monotonic sequence numbers and SHA-256 chaining on every approval.
6. **What-if speed and attribution (RL-6).** Shocks propagate in under 200 ms with attribution summing to 100.0%.
7. **Deterministic replay (RL-7).** A workstation outage serves a labelled verified replay, never invented state. The copilot never replays (ADR-019): its outage is a 503.

## 5. Provenance labels

Every quantitative claim in code, tests, fixtures, docs and UI carries a tag: `[BRIEF]` (from `docs/brief/*`), `[ASSUMPTION]`, `[ILLUSTRATIVE]` (non-production fixture), `[TARGET]` (SLO), `[SPIKE]` (exploratory; needs an `S-NN` id), `[MEASURED]` (a result our harness produced; allowed in repo-level `docs/`, not in `EIOS/docs/`). `label_check` enforces it on `EIOS/docs`.

UI decision (2026-10-14, user): the cockpit does not show per-figure `DEMO` or `[ILLUSTRATIVE]` chips, the green "figures filled" banner, or a synthetic-data marker. Other citation tags still show on a figure, and a figure's popover states its data origin and source. Provenance stays in the wire contract (`data_origin`, per-figure source and as-of) and in docs, code and fixtures. Consequence: nothing on screen says the data is synthetic, so do not put this build in front of anyone who could take it for production data; if real data is wired, restore a visible cue first.

Honesty rule for gaps: a figure nothing measured is absent, `NO_DATA` or `NOT_MEASURED`, never zero and never healthy.

## 6. Environments (Google Cloud)

- Projects: `eios-hackathon` (dev sandbox and control: Terraform state bucket `eios-tfstate-eios-hackathon`, GitHub OIDC pool `eios-ci`, the regulation corpus bucket and Agent Search data store `eios-regulations-dev`), `eios-hackathon-stage` (unused), `eios-hackathon-prod` (prod-like, hosts the demo). `spatial-cat-489006-a4` is legacy and is the gcloud default on this machine: **always pass `--project eios-hackathon`** and set `GOOGLE_CLOUD_QUOTA_PROJECT`.
- Public demo: `https://eios-web-562008989053.us-central1.run.app` (Cloud Run `eios-web`, the only public surface). `eios-api` is private: the web service sends its own ID token in `X-Serverless-Authorization` so the operator's Firebase token in `Authorization` passes through. Browser calls stay same-origin via the proxies in `web-prototype/src/app/api`.
- Infra: `EIOS/infra/envs/prod-like` (Terraform; `terraform.tfvars` is local and git-ignored, contents in the runbook; `terraform init -backend-config=bucket=eios-tfstate-eios-hackathon`). Dev sandboxes live in `infra/sandboxes/*` with their own state; a literal project id on disk trips `infra_checks`, so pass it with `-var-file` from outside the tree. Dev applies are allowed after the plan is shown; prod-like apply, Model Armor and any deploy need explicit approval. Images deploy by digest (`EIOS/services/cloudbuild.cockpit.yaml`), built as the least-privilege `pipeline@` identity. **Never deploy without explicit approval.**
- Operators: `uv run python -m tools.seed_demo_operators --project <id> --credentials-file <new file>`. Sign-up is disabled.
- Env vars the startup guards read: `EIOS_ENVIRONMENT` (dev/test allow local fallbacks; anything else refuses to start without the real thing), `EIOS_AUTH_MODE=firebase` + `EIOS_FIREBASE_PROJECT_ID`, `EIOS_PERSISTENCE=firestore` + `EIOS_FIRESTORE_DATABASE` (`eios-state`), `EIOS_KMS_KEY_VERSION` (full cryptoKeyVersions path), `EIOS_CORS_ORIGINS` (explicit, never `*`), `EIOS_CASHIER_WEBHOOK_SECRET`, `EIOS_HMAC_SALT` (at least 32 bytes outside dev/test, Secret Manager), `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `EIOS_GEMINI_MODEL` (the model id lives in config/tfvars only), `EIOS_KNOWLEDGE_DATA_STORE` (regulation index; unset means the tool says none is configured), `EIOS_DATA_PLANE`.
- Live smoke tests (skipped by default): set `GOOGLE_CLOUD_QUOTA_PROJECT` and `GOOGLE_CLOUD_PROJECT` to the project, plus `EIOS_TEST_CLOUD=1`, `EIOS_GEMINI_MODEL`, `EIOS_KMS_KEY_VERSION`, then `uv run pytest tests/integration tests/ontology -k "live or firestore"`. Without the quota project, ADC bills the wrong one (SERVICE_DISABLED).
- Recorded exceptions are in `EIOS/docs/environments.md`.

## 7. Rules and gotchas

- **Honesty at every layer.** Never fabricate a backend answer. Proxies relay real status codes; outage is 503 `offline`; workstations may serve a *labelled* replay but never mask 401/403. `kms_signature_verified` comes from verifying the signature, never from a non-empty field.
- **ADR-002 is open:** vendor LLM SDK imports and model ids are allowed only in `src/eios/llm_gateway/providers/` and `config/`, tests included (use a neutral model name, re-export SDK errors from the provider module). `open_decision_check` fails otherwise.
- **Tool descriptions** (`ontology/omcp/port/descriptions.py`) carry no digits (a test enforces it). A new capability needs a description, a row in `agent_gates/capability_map.yaml`, an offline route in `agent_gates/adapters/toolport_routes.py` and a sample in `tests/ontology/port/test_safety.py`.
- **`label_check`:** every number in docs needs a tag; `[SPIKE]` needs `S-NN`, else use `[ASSUMPTION]`.
- **`infra_policy`:** a Cloud Run service runs as an identity of the same name; service-account ids need 6+ chars; `allUsers` only via `allow_public_invocation`; identities must be in `infra/identities.yaml`.
- **Gemini 3.x** is served from the `global` endpoint only (regional 404s). Thinking tokens count against `max_output_tokens`. A platform-written function call needs `thought_signature=b"skip_thought_signature_validator"`. An ADK `LlmRequest` cannot be deep-copied (tools hold locks). google-genai automatic function calling fails on Python 3.14 here: keep it off and run tools yourself. Endpoint latency is erratic (the same question took 7 s, then hit the 30 s deadline): measure per stage before blaming code.
- **Metric Auditor:** dates, timestamps, `v`-versions, statutory citations, identifier codes and list numbering are exempt; unit suffixes need a word boundary (`1.2 bps` is not billions). Any other number must trace to a tool result.
- **Agent judges** (`src/eios/agent_gates/core/`): stdlib only, relative imports (they must parse under Python 3.12 for `agents-cli eval grade`). Validate a judge change against real model output with `--runtime recorded`, not only the synthetic corpus; the first live run found a bug the corpus could not.
- **Statistics:** standardise before a ridge fit (the penalty is in raw units); take the median of several placebo runs (one run fails a true edge one time in twenty); control for trend and season on revenue edges.
- **KMS:** `roles/cloudkms.signer` signs but cannot read the public key; verifying needs `roles/cloudkms.publicKeyViewer`. A service that does both needs both.
- **Cloud Run:** the ID-token audience is the URL Cloud Run reports (`status.url`), never a hand-built one. New service accounts and invoker bindings take a minute or two to propagate; retry before debugging. The API builds its engines during start-up (about 54 s on Cloud Run `[MEASURED]`), so a revision is ready only when it can answer, and `min_instances = 1` keeps one warm. Image builds: the least-privilege `pipeline@` needs `roles/storage.objectViewer` on the `_cloudbuild` bucket and the operator needs `serviceAccountTokenCreator` on it; build with `--service-account projects/<p>/serviceAccounts/pipeline@...` and `--billing-project <p>`. A full prod-like apply is unsafe until the evidence-bucket lock, the guardrails and the phone sign-in block are decided: use targeted plans.
- **Firestore:** transactional appends and updates with jittered retry; all instances use the same named database. In-memory stores are dev/test only and refused when deployed.
- **Next.js:** `next.config.ts` sets `typescript.ignoreBuildErrors`, so run `npx tsc --noEmit` yourself; delete stale `.next` if `tsc` shows bogus errors. `next dev` rewrites `web-prototype/AGENTS.md`: revert it before committing. `NEXT_PUBLIC_*` values reach the browser only as written-out `process.env.NEXT_PUBLIC_X` references (a bare `process.env` object is empty there: auth reads as disabled and every call is a 401 that falls back to replay); verify a deployed build by grepping its `/_next/static` chunks for the key. The web image copies `public/`, so keep that folder (an empty `.gitkeep` is enough).
- **Pre-existing, unrelated to feature work:** collection errors in `tests/fixtures/faulty_changes/coverage` and `tests/evals/*` on fresh checkouts; local `ruff check` flags the import order of `tests/evals/test_e2e_eval_harness.py` but CI's ruff accepts the original (trust CI; "fixing" it locally breaks CI); `test_quarantine` and the ADR record backfill test fail on `main`; timing benchmarks (`test_run_benchmark`, `test_dq_status_endpoint_performance`, `test_metric_engine`) flake under load and pass alone; `repo_checks` findings on `main`; mypy debt is quarantined until 2026-11-24.
- **Never `git add -A` over infra or build dirs** (a Terraform `tfplan` was once committed; `repo_checks` now blocks it; policy is no history purge and no force-push to `main`). Web key rotation: bump the id in `infra/envs/prod-like/cockpit.tf` (current `eios-web-auth-r2`; deleted ids stay reserved), apply, rebuild the web image, redeploy.
- **Shell:** zsh on macOS. Quote globs (`--include='*.py'`), do not rely on unquoted variables splitting into words, use `sed -i ''`, and check each step of an `&&` chain (a failed `sed` silently skips the rest). `ruff format` can reflow strings, so re-read before a scripted replace.
- **Ports & CORS:** Standard servers run on 3000 (Next.js web) and 8002 (FastAPI backend); port 8000 is legacy. Alternative ports: 3012 (web), 8012 (gateway). When running web on port 3012, ensure the backend includes port 3012 in `DEV_CORS_ORIGINS` (or start with `EIOS_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3012,http://127.0.0.1:3012"`) and pass `EIOS_BACKEND_URL=http://127.0.0.1:8002` to Next.js so proxies and direct fetches do not get blocked by CORS. Kill only your own PIDs.
- **Cockpit Graph Selection Contract:** In `TopologicalGraphCanvas`, clicking peripheral counterparties (mule accounts, payment agents, device tokens) must ONLY update local inspector state (`setSelectedNode`). Never call `selectEntity(node.id)` on peripheral nodes—`selectEntity` mutates global `activeEntityId`, triggering an API reload and resetting the inspector back to the case seed. `focalId` must remain anchored to the case seed dossier (`activeTriageItemId` / `CR84920`) so force simulation doesn't pull counterparties to (0,0) and jitter.
- **Performance & Core Web Vitals:** CWV benchmarks (LCP < 1.2s, CLS < 0.05, JS Heap ~7 MB) are measured against the production bundle (`npm run build && npm run start`). Dev mode (`npm run dev` on 3000) has on-the-fly TS compilation (2.8s render delay) and HMR memory overhead (120+ MB), which is normal for development.

## 8. How we work

- **Plan short, build 80/20, no spec-kit.** One short plan with the tasks inline; the design goes in a `docs/*.md` note and the PR text. Read the existing spec (`specs/NNN`) before changing what it describes.
- **Eval first, TDD, 80% coverage** on new code. Engines are judged against what their world planted, agent changes through the agent port (`src/eios/agent_gates/port.py`) against the golden cases, never by the agent itself. Report measured results, including the ones that disappoint.
- **Git:** trunk-based, one short-lived branch per milestone in the main checkout (not scratchpad worktrees, which the IDE cannot see; use a worktree only for genuinely parallel work), squash-merge, conventional commits, no Co-Authored-By trailers, delete the branch after merge (squash leaves it behind; verify the PR shows MERGED first). One PR per milestone; a stacked PR retargets to `main` once its base merges. Merge only with green CI and an up-to-date branch, and only when the user has said you may. Another agent owns the design branch: do not touch its checkout.
- **CI:** 15+ gates plus CodeQL (logging a secret in clear text is a real finding). Dependabot lockfile conflicts: take `main`'s `package.json`/lock, then `npm install <pkg>`.
- **No long evals by default.** Run unit tests and the static gates; run a live baseline, a multi-repeat run or any spend only when the user says so.
- **Context:** start a fresh session per milestone; state lives in the docs above and memory. Long jobs get a log line per step and run in the background.

## 9. State and next steps

Merged: real KMS signing, durable Firestore ledger and approvals, signed hub-routed staging, Firebase auth with RBAC and four-eyes, Cloud Run with Terraform, agent quality gates (spec 022) and the typed tool port (spec 023), the ADK runtime (spec 021, ADR-019; the legacy copilot, LangGraph mesh and runtime flag are deleted, ADR-016 Superseded), then the data and knowledge plan phases 1-3 (engine-backed AML, partner and compliance planes; regulation retrieval through Agent Search, #52-#56). The last live agent baseline (`docs/agent-baseline.md` section 7) predates all of that: re-measure before quoting it.

Merged since: #59-#67, #109 (Operations Board domain architecture and causal graph overlays), #110-#111 (Partner radar lead-time evaluation & disengagement risk score), #112 (CLS layout shift elimination, LCP acceleration, Cloud CDN caching, package import treeshaking). Active branch: PR #113 (SonarQube MQR security/blocker fixes, AML node dragging & focalId stabilization, canvas 60 FPS frame optimization). Executive and operations on engines; the model registry with the fastest model as default, per-call timing, hedge (median turn 2.0 s against 7.3 s, `docs/assistant-latency.md`); real turns feed the board's agent objectives (in-memory window, no BigQuery telemetry by decision); the warm tier on BigQuery (`docs/warm-tier.md`: contract-driven tables, loader, cost-guarded named-query store, `get_account_history`, parity eval, all measured); reviewer access (shared judge accounts and a login-page card, `EIOS/docs/runbooks/cockpit-deploy.md`).

**Deployed (2026-10-15, `eios-hackathon-prod`; read the live revisions with `gcloud run services describe`)**: Model Armor, the copilot rate limits (per operator and per instance, `EIOS/docs/runbooks/cockpit-deploy.md`; verified live: the 21st request in a minute is a 429), the BigQuery warm tier (history loaded: 17,646 events, 6,000 accounts; `EIOS_WARM_BACKEND=bigquery`), one warm API instance, the login card and the owner mailbox as `compliance_head`. A signed-in reviewer gets live engine data (not replay) and history answers in 3.8-4.6 s from BigQuery `[MEASURED]`. Deploys go through targeted Terraform plans from a clean `main` tree, with the local tfvars kept outside the repo; never run a full prod-like apply until the evidence-bucket lock, the guardrails and the phone sign-in block are decided.

Open risks: the reviewer password is public by design (only the copilot is rate-limited; the web proxy drops the `Retry-After` header, the seconds are in the message); remove the card (`demo_access`) and reset or disable the judge accounts after the review. The 13th AML capability is unmeasured against the live baseline (the fast model took extra tool rounds before the name fixes). Six of the 83-turn baseline failures were fixed in PR #61; three grader false positives remain (`docs/assistant-latency.md`).

Remaining work is tracked as GitHub issues #70-#76 (read them first). Phases, in the user's order: **5** ambient dossiers (precomputed, cached in Firestore), **7** MCP and A2A, and the **financial geospatial** feature (`docs/financial_geospatial.md`; reference geography from public BigQuery datasets is the second use of the warm tier). Done: **6** (latency, Model Armor, the board's agent objectives) and **4** (warm tier). BigQuery Graph is in use by the geo feature in dev: property graph `warm_graph.aml_geo`, GQL jobs on the Enterprise reservation `eios-graph` (baseline 0, autoscale 50, named per job), local DuckDB double, measured parity (`docs/geospatial-milestones.md`, N1).

Open items, in order of value:
1. **Latency** (mostly done, see above). Left: a live quality baseline on the new default model (needs the owner's go), and watching a real stall to prove the hedge (the `timing_ms` field on each answer shows per-call time).
2. **Before the next deploy** (owner approved Model Armor and Gen AI Enterprise on 2026-10-15; deploy itself still needs its own go): Model Armor templates (Terraform) and `GOOGLE_GENAI_USE_ENTERPRISE` (`docs/runbooks/cockpit-deploy.md`); without them every copilot query answers 503. Never deploy without explicit approval.
3. Assistant follow-ups: let the model repeat a number that appears in its own quote (needs adversarial tests); a 503 turn leaves an unanswered question and the next reply summarises the backlog; SAR drafts do not cite the licensing jurisdiction's rule; "Show in dossier" does not highlight the source card.
4. RL-2 and RL-7 are `NOT_MEASURED` on the operations board by design; the nine runbooks other than warm-start restore are a catalogue only; identity conflicts are not computed on the engine plane.
5. Product direction in `docs/financial_geospatial.md`: regulator-grade AML investigator, geography as an evidence lens.
6. Deploy via GitHub Actions workload identity (pool `eios-ci`), apply Terraform to stage and dev, close ADR-002, re-enable org-policy guardrails.
