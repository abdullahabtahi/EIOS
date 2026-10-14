# CLAUDE.md

Guidance for Claude Code in this repository. Keep it short; link, don't copy. If a fact is in the code or a doc, point to it.

## 1. Orientation

Forward Deployed Engineering (FDE) engagement, POC to production, for the **Enterprise Intelligence Operating System (EIOS)**. Client persona is Deriv (briefs in `docs/brief/`). `EIOS/` is the production root: Python backend (`uv`, Python 3.14) and the Next.js cockpit in `EIOS/web-prototype/` (its own `CLAUDE.md` holds UI rules and the persona/workstation matrix). Feature specs: `specs/`.

Read the doc for the area you touch, not all of them:

| Area | Doc |
|---|---|
| ADK migration status and decisions | `docs/adk.md`, `docs/adk-research.md` |
| Agent jobs, tool catalogue, topology | `docs/agent-architecture.md` |
| Measured "before" picture of the copilot | `docs/agent-baseline.md` |
| First measured workflow, metrics M1-M6 | `docs/lighthouse.md` |
| Data platform, warm tier, DDD contexts | `docs/data-strategy.md` |
| Geo/AML product direction | `docs/financial_geospatial.md` (v3 draft) |
| Deploy, environments, exceptions | `docs/runbooks/cockpit-deploy.md`, `EIOS/docs/environments.md` |

## 2. Commands

Backend, from `EIOS/`:
- `make setup`, `make test` (`-n auto`), `make lint`, `make types` (strict mypy), `make check` (all PR gates, same `config/gates.yaml` as `.github/workflows/pr.yml`, reports in `evals/reports/`)
- One test: `uv run pytest tests/cockpit/test_server_gateway.py::test_name -q`
- Network/cloud tests are off by default: `EIOS_TEST_NETWORK=1` (markers `requires_network`, `requires_emulator`, `requires_cloud`)
- Gateway: `uv run uvicorn eios.cockpit.server:app --port 8002` (what `api-bridge.ts` falls back to on localhost)
- Agent quality gates (spec 022; code `src/eios/agent_gates/`, cases `evals/golden/`, suites `evals/agent/`), run with `PYTHONPATH=src:.`:
  - Baseline offline: `python -m evals.agent.baseline --runtime adk` (scripted model, free). Do not run live or multi-repeat evals unless the user asks.
  - Live (spends money, needs `EIOS_AGENT_EVAL_MAX_TURNS` and the GCP vars in section 6; ~40 min for today's copilot): add `--live --repeats 1 --out evals/reports/agent_baseline_live`
  - Re-grade a saved run with no model call: `--runtime recorded --records <records.jsonl>`
  - Faithfulness over stored turns: `python -m evals.agent.faithfulness_suite --records evals/recorded --twice`

Web, from `EIOS/web-prototype/`: `npm run dev|build` (both `--webpack`), `npm run lint`, `npm test` (vitest; one file: `npx vitest run <path>`), `npx tsc --noEmit` must be 0 errors.

## 3. Architecture

Layers consume the one below only through contracts:
- **L0 `foundry/`**: seeded synthetic generators. All current data is synthetic.
- **L1 `ingestion/`, `contracts/`**: Pub/Sub, contract validation (breach goes to DLQ, never dropped), DuckDB hot state with Parquet warm start.
- **L2 `ontology/`**: `metrics/` registry (ADR-003), `graph/` with CGNAT hub suppression (ADR-004), `omcp/` the tool server agents must use, `actions/` Action Intents (`intent_hub.py` validates, signs, ledgers; `signer.py` is Cloud KMS when deployed, local-dev only in dev/test), `auditor/` the Metric Auditor Gate.
- **L3 `assistant/`**: the ADK assistant (ADR-019, spec 021) is the only copilot runtime. One agent per workstation over the governed tool port (`ontology/omcp/port`), a drafter that writes `{{fact:id}}` placeholders and an assembler that fills every figure from a tool result of the same turn (a number the model types is rejected; three failed drafts fail closed), ADK Firestore sessions, Model Armor screening, a 30 s turn deadline. An outage is a plain 503 `offline`; there is no replay and no legacy fallback. `cockpit/assistant_gateway.py` builds it; `llm_gateway/` is provider-neutral and the assistant reaches Google types through `llm_gateway/providers/adk_types.py`.
- **Domain modules** (`aml/`, `churn/`, `fraud/`, `synthesis/`) produce the numbers L3 narrates.
- **L4 `cockpit/`**: `server.py` FastAPI gateway; `governance_runtime.py` assembles signer, ledger, hub and WORM from env; `auth.py` verifies Firebase tokens (analyst, approver, compliance_head). `eios.api.app` mounts the cockpit and domain routers and is what the container runs.

Known gaps: workstation payloads are mostly fixtures, and `api-bridge.ts` still falls back to labelled fixtures (churn radar, AML graph, partner ontology) when the backend is down, so a working UI does not prove backend wiring. The copilot has no client-side fallback.

Process gates: add gates as rows in `config/gates.yaml`, never as runner edits. Quarantined gates (`config/quarantine.yaml`) fail the run after `expires`. The lint gate also runs `tools.repo_checks` (file size, forbidden literals, frozen models, pinned dependencies, no tracked plan/state/key files). `adr_check` needs `docs/evidence/adrs/` to agree with the index in `docs/spikes_and_adrs.md`.

## 4. Constitutional invariants (non-negotiable)

1. **No LLM-computed metrics (RL-1).** Every number comes from a deterministic engine (DuckDB semantic engine, BigQuery job, Flink). The LLM synthesises and explains.
2. **No autonomous write-back (RL-2).** Agents propose only. Any state change needs a Cloud KMS-signed (ECDSA P-256), expiring Action Intent approved by a human under four-eyes.
3. **Honest uncertainty (RL-3).** A causal claim shows as causal only if the placebo refuter p > 0.05 and confidence >= 0.80; otherwise "Correlation Only".
4. **CGNAT hub suppression (RL-4).** Shared-IP nodes with degree > 100 are collapsed out of laundering rings.
5. **WORM decision ledger (RL-5).** Monotonic sequence numbers and SHA-256 chaining on every approval.
6. **What-if speed and attribution (RL-6).** Shocks propagate in under 200 ms with attribution summing to 100.0%.
7. **Deterministic replay (RL-7).** An outage serves verified cached replay, never invented state.

## 5. Provenance labels

Every quantitative claim in code, tests, fixtures, docs and UI carries a tag: `[BRIEF]` (from `docs/brief/*`), `[ASSUMPTION]`, `[ILLUSTRATIVE]` (non-production fixture), `[TARGET]` (SLO), `[SPIKE]` (exploratory; needs an `S-NN` id), `[MEASURED]` (a result our harness produced). `label_check` enforces it on docs.

UI decision (2026-10-14, user): the cockpit does not show per-figure `DEMO` or `[ILLUSTRATIVE]` chips, the green "figures filled" banner, or a synthetic-data marker. Other citation tags (`[BRIEF]`, `[TARGET]`, `[ASSUMPTION]`) still show on a figure, and a figure's popover still states its data origin and source. Provenance stays in the wire contract (`data_origin`, per-figure source and as-of) and in docs, code and fixtures. Consequence to remember: nothing on screen says the data is synthetic, so do not put this build in front of anyone who could take it for production data; if real data is wired, restore a visible cue first.

## 6. Environments (Google Cloud)

- Projects: `eios-hackathon` (dev sandbox and control: Terraform state bucket `eios-tfstate-eios-hackathon`, GitHub OIDC pool `eios-ci`), `eios-hackathon-stage` (unused), `eios-hackathon-prod` (prod-like, hosts the demo). `spatial-cat-489006-a4` is legacy; nothing depends on it.
- Public demo: `https://eios-web-562008989053.us-central1.run.app` (Cloud Run `eios-web`, the only public surface). `eios-api` is private: the web service sends its own ID token in `X-Serverless-Authorization` so the operator's Firebase token in `Authorization` passes through. Browser calls stay same-origin via the proxies in `web-prototype/src/app/api`.
- Infra: `EIOS/infra/envs/prod-like` (Terraform; `terraform.tfvars` is local and git-ignored, contents in the runbook; `terraform init -backend-config=bucket=eios-tfstate-eios-hackathon`). Images deploy by digest (`EIOS/services/cloudbuild.cockpit.yaml`), built as the least-privilege `pipeline@` identity. **Never deploy without explicit approval.**
- Operators: `uv run python -m tools.seed_demo_operators --project <id> --credentials-file <new file>`. Sign-up is disabled.
- Env vars the startup guards read: `EIOS_ENVIRONMENT` (dev/test allow local fallbacks; anything else refuses to start without the real thing), `EIOS_AUTH_MODE=firebase` + `EIOS_FIREBASE_PROJECT_ID`, `EIOS_PERSISTENCE=firestore` + `EIOS_FIRESTORE_DATABASE` (`eios-state`), `EIOS_KMS_KEY_VERSION` (full cryptoKeyVersions path), `EIOS_CORS_ORIGINS` (explicit, never `*`), `EIOS_CASHIER_WEBHOOK_SECRET`, `EIOS_HMAC_SALT` (at least 32 bytes outside dev/test, Secret Manager), `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `EIOS_GEMINI_MODEL` (the model id lives in config/tfvars only).
- Live smoke tests (skipped by default): set `GOOGLE_CLOUD_QUOTA_PROJECT` and `GOOGLE_CLOUD_PROJECT` to the project, plus `EIOS_TEST_CLOUD=1`, `EIOS_GEMINI_MODEL`, `EIOS_KMS_KEY_VERSION`, then `uv run pytest tests/integration tests/ontology -k "live or firestore"`. Without the quota project, ADC bills the wrong one (SERVICE_DISABLED).
- Recorded exceptions are in `EIOS/docs/environments.md`.

## 7. Rules and gotchas

- **Honesty at every layer.** Never fabricate a backend answer. Proxies relay real status codes; outage is 503 `offline`; workstations may serve a *labelled* replay but never mask 401/403. The copilot never replays: an outage is 503. `kms_signature_verified` comes from verifying the signature, never from a non-empty field.
- **ADR-002 is open:** vendor LLM SDK imports and model ids are allowed only in `src/eios/llm_gateway/providers/` and `config/`, tests included (use a neutral model name, re-export SDK errors from the provider module). `open_decision_check` fails otherwise.
- **`label_check`:** every number in docs needs a tag; `[SPIKE]` needs `S-NN`, else use `[ASSUMPTION]`.
- **`infra_policy`:** a Cloud Run service runs as an identity of the same name; service-account ids need 6+ chars; `allUsers` only via `allow_public_invocation`; identities must be in `infra/identities.yaml`.
- **Gemini 3.x** is served from the `global` endpoint only (regional 404s). Thinking tokens count against `max_output_tokens`. google-genai automatic function calling fails on Python 3.14 here: keep it off and run tools yourself.
- **Metric Auditor:** dates, timestamps, `v`-versions, statutory citations, identifier codes and list numbering are exempt; unit suffixes need a word boundary (`1.2 bps` is not billions). Any other number must trace to a tool result.
- **Agent judges** (`src/eios/agent_gates/core/`): stdlib only, relative imports (they must parse under Python 3.12 for `agents-cli eval grade`). Validate a judge change against real model output with `--runtime recorded`, not only the synthetic corpus; the first live run found a bug the corpus could not.
- **KMS:** `roles/cloudkms.signer` signs but cannot read the public key; verifying needs `roles/cloudkms.publicKeyViewer`. A service that does both needs both.
- **Cloud Run:** the ID-token audience is the URL Cloud Run reports (`status.url`), never a hand-built one. New service accounts and invoker bindings take a minute or two to propagate; retry before debugging.
- **Firestore:** transactional appends and updates with jittered retry; all instances use the same named database. In-memory stores are dev/test only and refused when deployed.
- **Next.js:** `next.config.ts` sets `typescript.ignoreBuildErrors`, so run `npx tsc --noEmit` yourself; delete stale `.next` if `tsc` shows bogus errors.
- **Pre-existing, unrelated to feature work:** collection errors in `tests/fixtures/faulty_changes/coverage` and `tests/evals/*` on fresh checkouts; local `ruff check` flags the import order of `tests/evals/test_e2e_eval_harness.py` but CI's ruff accepts the original (trust CI; "fixing" it locally breaks CI); flaky `test_quarantine.py` and timing benchmarks (`test_benchmark`, `test_metric_engine`, `test_dq_monitor`); mypy errors in `eios.conversation`, ingestion and `llm_gateway`; `repo_checks` findings on `main`.
- **Never `git add -A` over infra or build dirs** (a Terraform `tfplan` was once committed; `repo_checks` now blocks it; policy is no history purge and no force-push to `main`). Web key rotation: bump the id in `infra/envs/prod-like/cockpit.tf` (current `eios-web-auth-r2`; deleted ids stay reserved), apply, rebuild the web image, redeploy.
- **Shell:** zsh. Quote globs (`--include='*.py'`) and do not rely on unquoted variables splitting into words.

## 8. How we work

- **Spec-driven** (`specs/`): `spec.md` is the contract. Plan in the Claude Code harness (plan mode), one short plan with the tasks inline, built 80/20; the spec-kit skills are retired. Read the existing `spec.md` (and any `plan.md`/`tasks.md`) before adding models or endpoints.
- **Eval first, TDD, 80% coverage** on new code. Agent changes are judged through the agent port (`src/eios/agent_gates/port.py`) against the golden cases, never by the agent itself.
- **Git:** trunk-based, one short-lived branch per spec in the main checkout (not scratchpad worktrees, which the IDE cannot see; use a worktree only for genuinely parallel work), squash-merge, conventional commits, no Co-Authored-By trailers, delete the branch after merge (squash leaves it behind; verify the PR shows MERGED first). PR when implementation lands, not per artifact. Merge only with green CI and an up-to-date branch, and only when the user has said you may.
- **CI:** 15+ gates plus CodeQL (logging a secret in clear text is a real finding). Dependabot lockfile conflicts: take `main`'s `package.json`/lock, then `npm install <pkg>`.
- **No long evals by default.** Run unit tests and the static gates; run a live baseline, a multi-repeat run or any spend only when the user says so.
- **Context:** start a fresh session per spec; state lives in the spec, the docs above and memory. Long jobs (the live baseline) get a log line per step and run in the background.

## 9. State and next steps

Done and merged: real KMS signing, durable Firestore ledger and approvals, signed hub-routed staging, Firebase auth with RBAC and identity-bound four-eyes, honest proxies, Cloud Run with Terraform, spec 022 agent quality gates and the measured baseline (`docs/agent-baseline.md`), spec 023 typed tool port (`eios.ontology.omcp.port`), the ADK pins (#40), and spec 021 (ADK runtime, ADR-019 Accepted). The legacy copilot (`conversation/`), the LangGraph mesh, the `EIOS_ASSISTANT_RUNTIME` flag and `langchain-core`/`langgraph` are deleted; ADR-016 is Superseded.

The assistant today (run 3: cap 45, one repeat, `docs/agent-baseline.md` section 7): 50 pass, 7 fail, 5 inconclusive `[MEASURED]`; faithfulness 99.0% `[MEASURED]` and p95 17.0 s counting timeouts `[MEASURED]`, against targets of 100% and 15 s `[TARGET]`, not met. A clean turn takes 4 to 8 s `[MEASURED]`; an open-ended question ("what should I do about X?") can hit the 30 s deadline `[MEASURED]`. The legacy copilot was retired before the targets were met by the user's decision (recorded in ADR-019). The cockpit chat lives in the dossier column behind a Dossier | Chat switch (one thread per workstation; see memory `project-chat-workspace-spec-030`).

Open items, in order of value:
1. **Before the next deploy**: Model Armor templates (Terraform, ask first) and `GOOGLE_GENAI_USE_ENTERPRISE` (`docs/runbooks/cockpit-deploy.md`); without them every copilot query answers 503. Never deploy without explicit approval.
2. Assistant quality: the three-repeat gating run (needs a separately approved cap, no long evals by default); the telemetry plugin; confirm the faithfulness judge also treats digit-bearing names as names (the assembler already does). A broad question about one entity now uses its signals tool alone (golden case `partner_open_ended`); a turn still costs one model call per tool round plus the draft, about 4 to 6 s each `[MEASURED]`.
3. Chat UX gaps: "Show in dossier" flips the tab but does not highlight the source card. A graph node you click becomes the entity on screen, so asking about it (for example `MULE-4920-20`) answers "not found", which is honest and by design.
4. `api-bridge.ts` fabricated fallbacks for the churn radar, AML graph and partner ontology.
5. Product direction in `docs/financial_geospatial.md`: regulator-grade AML investigator, geography as an evidence lens. Verify GLEIF and labelled-data licences before ingesting; Dekart is AGPL.
6. Deploy via GitHub Actions workload identity (pool `eios-ci`), apply Terraform to stage and dev, close ADR-002, re-enable org-policy guardrails.
