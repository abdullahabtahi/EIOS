# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 1. Repository Orientation

Forward Deployed Engineering (FDE) engagement, POC → Production, for the **Enterprise Intelligence Operating System (EIOS)**. `EIOS/` is the primary self-contained production root (Python backend via `uv`, Next.js cockpit in `EIOS/web-prototype/`). Requirement sources live in `docs/` (canonical briefs in `docs/brief/`); feature specs live in `specs/`. UI design rules and the persona/workstation matrix are in `EIOS/web-prototype/CLAUDE.md`.

---

## 2. Commands

Backend (run from `EIOS/`, Python 3.14 via `uv`):
- `make setup` (uv sync), `make test` (pytest `-n auto`), `make lint` (ruff check + format check), `make types` (strict mypy)
- **Single test**: `uv run pytest tests/cockpit/test_server_gateway.py::test_name -q`
- **Network-enabled tests**: `EIOS_TEST_NETWORK=1 uv run pytest -q` (default runs are offline; markers `requires_network`, `requires_emulator`, `requires_cloud`)
- **Agent quality gates** (spec 022): `evals/agent/`, judges in `src/eios/agent_gates/core/`. Baseline: `PYTHONPATH=src:. python -m evals.agent.baseline --runtime copilot`; faithfulness over stored turns: `python -m evals.agent.faithfulness_suite --records evals/recorded --twice`
- **All 14 PR gates**: `make check`. Same gates and same `config/gates.yaml` as `.github/workflows/pr.yml`; reports land in `evals/reports/`.
- Cockpit gateway: `uv run uvicorn eios.cockpit.server:app --port 8002` (the port `api-bridge.ts` falls back to on localhost)

Web (run from `EIOS/web-prototype/`): `npm run dev` / `build` (both `--webpack`), `npm run lint`, `npm test` (vitest; single file: `npx vitest run <path>`), `npx tsc --noEmit` must be 0 errors.

---

## 3. Architecture (big picture)

Layered, each layer consuming the one below only through contracts:
- **L0 `foundry/`**: seeded synthetic generators (hard negatives, sealed holdout, placebo edges). All current data is synthetic.
- **L1 `ingestion/`, `contracts/`**: Pub/Sub, then Pydantic contract validation (breach goes to DLQ, never silent drop), then DuckDB hot state with Parquet warm start.
- **L2 `ontology/`**: objects/links/actions/security markings. `metrics/` is the DuckDB semantic registry (ADR-003), `graph/` is NetworkX with CGNAT hub suppression (ADR-004), `omcp/` is the tool server agents must use, and `actions/` holds Action Intents: `intent_hub.py` (validates, signs, nonce-registers, ledgers; tokens carry an optimistic `revision`), `signer.py` (`CloudKMSActionSigner` in deployed envs, `LocalDevActionSigner` only in dev/test), `ledger_store.py` + `record_store.py` (in-memory or Firestore, atomic append/update/create), `sequencer.py` (hash chain), `worm.py` (signed checkpoints), `sink.py` (simulated write-back). `auditor/` is the Metric Auditor Gate.
- **L3 `conversation/`**: two paths. `copilot_engine.py` is what the cockpit uses (live Gemini via `google-genai`, SDK automatic function calling disabled, bounded allow-listed OMCP tool loop, bounded self-correction fed by the Metric Auditor, deterministic replay only on failure and always labelled `is_replay_fallback` + `fallback_reason`). `graph.py`/`supervisor.py` is the LangGraph blackboard mesh (ADR-016) with keyword routing and thin specialists; it is slated for migration to Google ADK. `llm_gateway/` (prompt lock, replay cache, `providers/vertex.py`) is the provider-neutral gateway; the copilot does not go through it yet.
- **Domain modules** (`aml/`, `churn/`, `fraud/`, `synthesis/` with SCM, forecast and AIPW) produce the deterministic numbers that L3 narrates.
- **L4 `cockpit/`**: `server.py` is the FastAPI gateway (workstations, simulate, stage/authorize, copilot, flywheel, audit verify). `governance_runtime.py` assembles signer + ledger + hub + shelf + WORM from env; `governance_shelf.py` is a view over the hub (real signature verification, errors propagate); `auth.py` verifies Firebase ID tokens, roles analyst/approver/compliance_head, and refuses to start unauthenticated outside dev. `eios.api.app` mounts the same cockpit routers plus the domain routers and is what the container runs. Workstation payloads are still largely fixtures; the web `api-bridge.ts` falls back to labelled fixtures when the backend is unreachable, so a working UI does not prove backend wiring. The browser's stage/authorize shelf actions are still client-side reducers that do not call the backend.

Process gates: new gates are rows in `config/gates.yaml` (never runner edits). Quarantined gates in `config/quarantine.yaml` fail the run after their `expires` date. The lint gate also runs `tools.repo_checks` (file size, forbidden literals, frozen models, pinned dependencies). `adr_check` requires ADRs in `docs/evidence/adrs/` to agree with the index in `docs/spikes_and_adrs.md`.

---

## 4. Constitutional Invariants (Non-Negotiable)

1. **LLMs Never Compute Business Metrics (Principle I / RL-1)**:
   - All numbers must originate from deterministic analytical engines (DuckDB Semantic Engine, BigQuery metrics job, or Flink streaming).
   - The LLM's role is synthesis, explanation, and draft narrative generation only.
2. **No Autonomous Write-Back (Principle II / RL-2)**:
   - Agents can only propose actions.
   - Every state mutation requires a Cloud KMS-signed (ECDSA P-256), expiring Action Intent approved by a human operator under Four-Eyes dual control.
3. **Honest Uncertainty & Causal Evidence Gate (Principle III / RL-3)**:
   - Causal vectors are displayed as verified causal only if placebo-treatment refuter $p > 0.05$ and confidence $\ge 0.80$. Otherwise, explicitly rendered as "Correlation Only".
4. **CGNAT False Positive Hub Suppression (Feature 010 / RL-4)**:
   - Shared IP gateway nodes with degree $k > 100$ are automatically collapsed and suppressed from false-positive money laundering rings.
5. **Immutable WORM Decision Ledger (Feature 011 / RL-5)**:
   - Monotonic sequence numbers with SHA-256 cryptographic chaining lock every approval action.
6. **Sub-200ms Parametric Propagation & 100% Attribution (Feature 002 / RL-6)**:
   - What-If shocks propagate in $< 200\text{ms}$ with verified $\sum \text{Attribution} = 100.0\%$.
7. **Deterministic Offline Replay Fallback (Principle VIII / RL-7)**:
   - Network partition or presentation outage triggers verified cryptographic cache replay, never hallucinated states.

---

## 5. Provenance & Labelling Regime

Every quantitative figure or claim in the codebase, tests, fixtures, and UI must carry an explicit provenance label:
- `[BRIEF]`: Cited directly from canonical business requirements (`docs/brief/*`).
- `[ASSUMPTION]`: Explicit operational assumption documented in architecture plan.
- `[ILLUSTRATIVE]`: UI walkthrough or mockup placeholder clearly labeled as non-production fixture.
- `[TARGET]`: Formal SLO or performance commitment.
- `[SPIKE]`: Temporary exploratory metric pending Architectural Decision Record (ADR).

---

## 6. Spec-Driven Workflow (Spec-Kit)

When developing or modifying features, follow the established spec pipeline in `specs/`:
```
Constitution → Specify → Clarify → Plan → Tasks → Analyze → Implement
```
- Skills: `speckit-<stage>` (plus `speckit-converge`).
- Always inspect existing `spec.md`, `plan.md`, and `tasks.md` in `specs/<feature-dir>/` before introducing new domain models or endpoints.

---

## 7. Environments and Deployment (Google Cloud)

Projects, all billed to one account: `eios-hackathon` (dev sandbox and control project: Terraform state bucket `eios-tfstate-eios-hackathon`, GitHub OIDC pool `eios-ci`), `eios-hackathon-stage` (created, unused), `eios-hackathon-prod` (the prod-like environment that hosts the public demo). `spatial-cat-489006-a4` is a shared legacy project; nothing here depends on it.

- Public demo: `https://eios-web-562008989053.us-central1.run.app` (Cloud Run `eios-web`, public, the only public surface). `eios-api` is private; the web service reaches it with its own ID token in `X-Serverless-Authorization` so the operator's Firebase token in `Authorization` passes through. Browser calls stay same-origin (`/api/v1/*` and `/api/cockpit/*` are proxies in `web-prototype/src/app/api`).
- Infra: `EIOS/infra/envs/prod-like` (Terraform). `terraform.tfvars` is git-ignored and local; its contents are in the runbook. Init with `terraform init -backend-config=bucket=eios-tfstate-eios-hackathon`. Release flow (images by digest): `docs/runbooks/cockpit-deploy.md` and `EIOS/services/cloudbuild.cockpit.yaml`. Build runs as the least-privilege `pipeline@` identity.
- Operators: provision with `uv run python -m tools.seed_demo_operators --project <id> --credentials-file <new file>` (writes a 0600 file; never prints passwords). Sign-up is disabled in Identity Platform.
- Runtime env vars the guards read: `EIOS_ENVIRONMENT` (dev/test allow local fallbacks; anything else refuses to start without the real thing), `EIOS_AUTH_MODE=firebase` + `EIOS_FIREBASE_PROJECT_ID`, `EIOS_PERSISTENCE=firestore` + `EIOS_FIRESTORE_DATABASE` (named db `eios-state`), `EIOS_KMS_KEY_VERSION` (full cryptoKeyVersions path), `EIOS_CORS_ORIGINS` (explicit, never `*`), `EIOS_CASHIER_WEBHOOK_SECRET` and `EIOS_HMAC_SALT` (token vault key, at least 32 bytes outside dev/test; Secret Manager), `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `EIOS_GEMINI_MODEL` (the model id lives in config/tfvars, never in source or tests).
- Live smoke tests (skipped by default): `GOOGLE_CLOUD_QUOTA_PROJECT=<project> GOOGLE_CLOUD_PROJECT=<project> EIOS_TEST_CLOUD=1 EIOS_GEMINI_MODEL=<model> EIOS_KMS_KEY_VERSION=<path> uv run pytest tests/integration tests/ontology -k "live or firestore"`. Local ADC bills API calls to its quota project, so set `GOOGLE_CLOUD_QUOTA_PROJECT` or you get SERVICE_DISABLED on the wrong project.
- Recorded exceptions (see `EIOS/docs/environments.md`): org-policy guardrails off in prod (no `orgpolicy.policyAdmin`), public invoker on the web service only, evidence-bucket retention lock off.

---

## 8. Hard-Won Rules and Gotchas

- **Honesty at every layer.** Never fabricate a backend answer. Proxies relay real status codes; outage is 503 `offline`, workstations may serve a *labelled* replay snapshot but never mask 401/403. Replay answers must set `is_replay_fallback`. A card's `kms_signature_verified` must come from verifying the signature, never from the field being non-empty.
- **ADR-002 is open**: vendor LLM SDK imports and model ids are allowed only in `src/eios/llm_gateway/providers/` and `config/`. This includes tests (use a neutral model name; re-export SDK error types from the provider module). `open_decision_check` fails otherwise.
- **`label_check`** scans docs: every number needs a provenance tag, and `[SPIKE]` must carry an `S-NN` id (use `[ASSUMPTION]` otherwise).
- **`infra_policy`**: a Cloud Run service must run as an identity of the same name; service-account ids need 6+ characters; `run_service` rejects `allUsers` except via the explicit `allow_public_invocation`; identities must be listed in `infra/identities.yaml`.
- **Gemini 3.x** is served from the `global` endpoint only (regional returns 404). Thinking tokens count against `max_output_tokens`. google-genai automatic function calling fails on Python 3.14 here: keep it disabled and run tools yourself.
- **Metric Auditor**: dates, timestamps, `v`-prefixed versions, statutory citations, identifier codes and list numbering are exempt; unit suffixes need a word boundary (`1.2 bps` is not billions). Anything else numeric must trace to a tool result.
- **KMS**: `roles/cloudkms.signer` can sign but cannot read the public key; verification needs `roles/cloudkms.publicKeyViewer` (the module's verifier role). The same service signing and verifying needs both.
- **Cloud Run**: ID-token audience must be the service URL as Cloud Run reports it (`status.url`), not a hand-built URL. New service accounts and invoker bindings take a minute or two to propagate; retry before debugging.
- **Firestore**: appends and updates are transactional with jittered retry; every instance must use the same named database. In-memory stores exist for dev/test only and are refused when deployed.
- **Next.js**: `next.config.ts` has `typescript.ignoreBuildErrors`, so run `npx tsc --noEmit` yourself. Stale `.next` output can produce bogus `tsc` errors; delete it.
- **Git/CI**: trunk-based, one small branch and PR per change, squash-merge, conventional commits, no Co-Authored-By trailers on commits. CI runs 15+ gates plus CodeQL (clear-text logging of secrets is a real finding). Dependabot lockfile conflicts: take `main`'s `package.json`/lock, re-run `npm install <pkg>`. Use `git worktree` when the main checkout has uncommitted work. `tests/fixtures/faulty_changes/coverage` and `tests/evals/*` collection errors on fresh checkouts are pre-existing; `tests/unit/tools/gates/test_quarantine.py` and a few timing benchmarks (`test_benchmark`, `test_metric_engine`, `test_dq_monitor`) fail or flake locally and are unrelated to feature work.
- **Never `git add -A` over infra or build dirs.** A Terraform `tfplan` (embeds state) was committed in PR #17; keys were rotated, `repo_checks` now fails CI on tracked plan/state/private-key files, and no history purge or `main` force-push is the deliberate policy. To rotate the web key (current id `eios-web-auth-r2`): bump the id in `infra/envs/prod-like/cockpit.tf` (deleted ids stay reserved), apply, rebuild the web image, redeploy.
- zsh: quote `--include='*.py'` globs.

---

## 9. State of the Work and Next Steps

Done (merged): real KMS signing, durable Firestore ledger/approvals, signed hub-routed staging, Firebase auth with RBAC and identity-bound four-eyes, honest proxies, Cloud Run deployment with Terraform, live copilot grounding (4 of 4 sample questions answered live).

Next, in priority order:
1. **Migrate the conversational agent from LangGraph to Google ADK** (user priority; the GenAI path has many bugs). Needs an ADR superseding 016 and spec 021. Keep the auditor egress, compliance-hold arbitration, KMS-signed human-in-the-loop interception, the allow-listed OMCP tool set (also expose OMCP as an MCP server) and the 3-cycle bound. Reduce correction-round latency (turns reached 50 to 65 seconds). Surface `is_replay_fallback` through the web proxy normalizer so the UI can badge replays.
2. Wire the browser's governed action shelf to the real stage/authorize endpoints (it is currently client-side only) and remove client-side fabricated copilot fallbacks.
3. Product strategy: `docs/financial_geospatial.md` (v3 draft, outside EIOS gate scans). Product is a regulator-grade AML investigator (alert triage plus SAR draft); geography is an evidence lens. Verify GLEIF and labelled-data licences before ingesting; OpenBB V5 is Apache-2.0 (V4 and earlier were AGPL; data terms stay per provider); Dekart is AGPL.
4. GitHub Actions deploy via workload identity (pool `eios-ci` exists), apply Terraform to stage and dev, close ADR-002, grant Org Policy Admin and re-enable guardrails. (`main` is already protected by the `main-protection` ruleset.)
