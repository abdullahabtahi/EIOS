# Runbook: deploy the cockpit (web + API)

Two Cloud Run services in the prod-like project: **eios-web** (the web service; public; the only public entry point; it signs
operators in and relays `/api/*` to the API) and **eios-api** (private; invoked only by the web service's
identity through `X-Serverless-Authorization`, so the operator's Firebase token in `Authorization` passes through).

## Architecture in one paragraph
Operator signs in with Identity Platform (email and password; sign-up disabled; role in the `role` custom claim).
The browser sends the ID token to cockpit_web. cockpit_web relays to cockpit_api with its own Google ID token. The
API verifies the operator token, enforces roles, signs Action Intents with Cloud KMS, and stores approval state and
the hash-chained decision ledger in Firestore (database `eios-state`).

## One-time setup (per environment project)
1. Enable base APIs: `cloudresourcemanager serviceusage iam iamcredentials orgpolicy cloudbilling billingbudgets`.
2. State bucket and CI federation pool exist in the control project (see `docs/runbooks/bootstrap.md`).
3. `cd EIOS/infra/envs/prod-like`, create `terraform.tfvars` (git-ignored; see the example), then
   `terraform init -backend-config=bucket=<state bucket>` and `terraform apply`.
4. Create the HMAC salt value once (the API refuses to start without it): `openssl rand -hex 32 | gcloud secrets versions add hmac_salt --data-file=-`. Then the webhook secret value: `openssl rand -hex 32 | gcloud secrets versions add cashier_webhook_secret --data-file=-`.
5. Provision operators: `uv run python -m tools.seed_demo_operators --project <id> --credentials-file <new file>`.

## Release
1. Grant the build identity read on the source bucket once: `roles/storage.objectViewer` on `gs://<project>_cloudbuild` for `pipeline@`.
2. Build both images as the pipeline identity (see the header of `EIOS/services/cloudbuild.cockpit.yaml`).
3. Put the two image digests in `terraform.tfvars` (`cockpit_api_image`, `cockpit_web_image`) and `terraform apply`.
4. Smoke test: sign in as each operator; stage, approve twice (two distinct approvers), verify the ledger.
5. A web-only release is enough when nothing under `EIOS/src`, `EIOS/services` or `EIOS/config` changed since the live `eios-api` revision was built (`git diff <that commit> HEAD -- EIOS/src EIOS/services EIOS/config`, with the commit found from the revision's creation time). Otherwise release the two services together: the web service calls API routes (ambient briefs, evidence replay, list changes, the shelf) that an older API revision may not have.
6. Check the public site after the release:
   - `/landing/orbit/f_001.webp?v=1` answers with `Cache-Control: public, max-age=31536000, immutable`, and `/landing/orbit/f_001.webp.json` answers 404 (generation prompts are kept in `asset-sources/`, not served).
   - A landing raster that changes needs a new `LANDING_ASSET_VERSION` in `src/components/landing/assets.ts`, because the old URL is cached for a year.
   - `/login` shows the evaluator guide link and the evaluator accounts card; signing in lands on `/cockpit/geospatial`, and the header shows a readable name (the account's display name, else the mailbox made readable).
   - The cockpit's icons render (the Material Symbols stylesheet loads from `src/app/cockpit/layout.tsx`, not from the root layout).

## ADK assistant
The cockpit's copilot endpoint is served by the ADK assistant (`src/eios/assistant/`, ADR-019) and nothing else; the
legacy copilot and the `EIOS_ASSISTANT_RUNTIME` switch were removed. **Prerequisite for every deploy:** the Model
Armor templates and `GOOGLE_GENAI_USE_ENTERPRISE` below must be set, or every copilot query answers 503 `offline`.
The live `eios-api` revision in `eios-hackathon-prod` carries both template variables and `GOOGLE_GENAI_USE_ENTERPRISE` (read from its
environment on 2026-10-19), so a redeploy from the same tfvars keeps them. There is no kill switch: to take the assistant out of service,
redeploy the previous revision.

| Variable | Value | Notes |
|---|---|---|
| `GOOGLE_GENAI_USE_ENTERPRISE` | `true` | Makes the model client use Vertex AI with the service identity instead of an API key. |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | project id, `global` | The current model generation is served from the `global` endpoint only. |
| `EIOS_GEMINI_MODEL` | model id | Lives in tfvars/config only (ADR-002). |
| `EIOS_PERSISTENCE`, `EIOS_FIRESTORE_DATABASE` | `firestore`, `eios-state` | Conversation sessions. Outside dev/test the service refuses to start without them: an in-memory thread would not survive a revision or be shared across instances. |
| `EIOS_MODEL_ARMOR_PROMPT_TEMPLATE`, `EIOS_MODEL_ARMOR_RESPONSE_TEMPLATE` | full template resource names | Both or neither. Outside dev/test the service refuses to start without both. They are created by `infra/modules/model_armor` (see below). If screening fails the turn is blocked, never passed through. |
| `EIOS_ASSISTANT_TURN_DEADLINE_S` | default 30 `[ASSUMPTION]` | A turn past this returns a labelled timeout, not a guess. |
| `EIOS_ASSISTANT_MAX_LLM_CALLS` | default 12 `[ASSUMPTION]` | Tool rounds plus up to three assembly attempts. |
| `EIOS_ASSISTANT_HISTORY_TURNS` | default 6 `[ASSUMPTION]` | Earlier turns the model reads; the stored thread keeps all of them. |

Behaviour on a model outage is a plain 503 `offline` with no answer body; the browser says the assistant is unavailable.
There is no replay of past answers for free-text questions (decision of 2026-10-14); workstation screens keep their own
labelled replay. The runtime's service account needs `roles/aiplatform.user` and Firestore access to `eios-state`, plus
`roles/modelarmor.user` once the templates exist.

## Model Armor templates (dev sandbox first)
The templates are a Terraform module, `infra/modules/model_armor`, applied on its own in the dev sandbox project through
`infra/sandboxes/model-armor` (its own state prefix; the full `envs/dev` skeleton is not touched). Filters: Responsible-AI
categories and malicious links on both templates, prompt injection and jailbreak on the prompt template, all at medium
confidence and blocking. Sensitive Data Protection is off on purpose: answers carry ids, names and amounts.

1. `cd EIOS/infra/sandboxes/model-armor`; pass the project id on the command line (`-var project_id=<id>`) rather than a tfvars file, which the infra policy gate flags when it holds a real id.
2. `terraform init -backend-config=bucket=eios-tfstate-eios-hackathon`, then `terraform plan` and read it. **Applying needs the user's say-so.**
3. After an apply, measure before choosing thresholds, with no model call:
   `PYTHONPATH=src:. uv run python -m evals.agent.screening_probe --template <prompt template name> --out <report.json>`.
   It screens every golden question (a block is a false positive) and every attack question, and times each call. Pass criteria are
   fixed in `evals/agent/screening_probe.py` before the run. Attacks that arrive inside a tool result are not screened by the plugin
   (the tool port marks such text untrusted), so a missed attack there is information, not a failure.
4. Then run the gateway locally with `EIOS_MODEL_ARMOR_PROMPT_TEMPLATE` and `EIOS_MODEL_ARMOR_RESPONSE_TEMPLATE` set to the two
   outputs, `GOOGLE_CLOUD_QUOTA_PROJECT` set to the sandbox project, and `GOOGLE_GENAI_USE_ENTERPRISE=true`. Measure the added latency, send an
   obvious injection, and read the matches in Cloud Logging before choosing thresholds for prod-like.
5. prod-like reuses the same module, adds `roles/modelarmor.user` for the `eios_api` identity, sets the two variables on the Cloud Run
   service, and needs its own plan, approval and deploy.

### Dev sandbox measurement (2026-10-14; the numbers are in PR #51)
- Applied: the API and the two templates. No false positive on the golden questions, no screening failure, and no block on real assistant answers.
- Latency was measured from a laptop over the internet, which misses the budget of 400 ms at p95 `[ASSUMPTION]`. The figure that matters is from Cloud Run in the same region and has not been measured: re-run `screening_probe` from inside `us-central1` before choosing prod-like thresholds.
- Attacks: Model Armor blocked one of the attack questions. It is a content-safety filter, not our access control: write attempts, impersonation, stage-then-approve and cross-scope requests are stopped by the tool port (role scoping, no approve or execute tool) and judged by the spec 022 attack gates.
- Cold start: the first screened turn after a restart was about twice as slow because the service connection opens lazily. The app now warms it in the background at startup (`assistant_gateway.warm_up`), and the first turn is then a normal turn.
- Open: whether Sensitive Data Protection is wanted, after reading real traffic.

## Known exceptions
- **Guardrails off** (`enforce_guardrails = false`) in eios-hackathon-prod: the deploying identity lacks
  `orgpolicy.policyAdmin`. Re-enable once granted. [ASSUMPTION: hackathon project]
- **Public invocation** is allowed for cockpit_web only (`allow_public_invocation`); the API stays private.
- **Evidence bucket retention lock** disabled (`evidence_lock_retention = false`) to avoid an irreversible lock.

## Reviewer access (hackathon review)
Shared accounts for reviewers and judges, shown on the login page as "Evaluator accounts" beside the evaluator guide link (`src/components/auth/login/evaluator-guide.tsx`). The card's note defaults in code to "client activity is synthetic, the reference layers are real public data"; a `note` in `demo_access` overrides it, so leave it out unless the text is true. The password is public by design, so the accounts only see the demo's synthetic data; rotate or remove them when the review ends.
1. Create the accounts: `EIOS_REVIEWER_PASSWORD=<12+ characters> uv run python -m tools.seed_demo_operators --project <id> --credentials-file <new file> --reviewers --skip-demo-operators`. Add `--owner-email you@example.com` to authorise a real mailbox as a `compliance_head` (its generated password goes to the credentials file). `--skip-demo-operators` keeps the three standard accounts' passwords unchanged.
2. Publish the card: set `demo_access` in the local tfvars (JSON, see `variables.tf`) and apply the web service. The web service reads it at run time from `EIOS_DEMO_ACCESS`; nothing is in git or in the image.
3. Take it down: remove `demo_access`, apply, then disable or rotate the accounts (reset their password with the same tool, or disable them in Identity Platform).

## Rate limits (protecting Gen AI spend)
Only the copilot route is limited, because it is the only path that calls the model and the reviewer accounts are shared and public. It uses the `limits` library (moving windows, in this instance's memory), keyed by the verified operator id, plus one cap for the whole instance. A question over a limit gets `429` with `Retry-After` and the chat says so; nothing is queued. A question is also capped at 2000 characters.
- `EIOS_RATE_COPILOT_PER_USER`: default `20/minute;600/day` per operator. `EIOS_RATE_COPILOT_GLOBAL`: default `3000/day` per instance. Both are `limits` rate strings; an invalid value is logged as an error and the default is used.
- `EIOS_RATE_LIMITS=off` disables them (local work only). Counters reset when an instance restarts, and with several instances the real ceiling is that many times the figure; `max_instances` and the budget alert are the outer bound. If instances multiply, point `limits` at a shared store (Memorystore for Redis).
- To see a refusal without spending anything, send questions with an empty `query`: they are counted, then refused with 422, and the 21st in a minute is a 429.

## Private deploy files
The prod-like variables, the reviewer password and the build key are kept out of the repo, on the owner's machine in `~/eios-private/` (owner-only; its `README.md` has the exact plan, apply and build commands). They are never committed. After each build, update the two image digests in `prodlike.tfvars`.
