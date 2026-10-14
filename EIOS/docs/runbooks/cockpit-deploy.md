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
4. Create the webhook secret value: `openssl rand -hex 32 | gcloud secrets versions add cashier_webhook_secret --data-file=-`.
5. Provision operators: `uv run python -m tools.seed_demo_operators --project <id> --credentials-file <new file>`.

## Release
1. Grant the build identity read on the source bucket once: `roles/storage.objectViewer` on `gs://<project>_cloudbuild` for `pipeline@`.
2. Build both images as the pipeline identity (see the header of `EIOS/services/cloudbuild.cockpit.yaml`).
3. Put the two image digests in `terraform.tfvars` (`cockpit_api_image`, `cockpit_web_image`) and `terraform apply`.
4. Smoke test: sign in as each operator; stage, approve twice (two distinct approvers), verify the ledger.

## ADK assistant
The cockpit's copilot endpoint is served by the ADK assistant (`src/eios/assistant/`, ADR-019) and nothing else; the
legacy copilot and the `EIOS_ASSISTANT_RUNTIME` switch were removed. **Prerequisite for the next deploy:** the Model
Armor templates and `GOOGLE_GENAI_USE_ENTERPRISE` below must exist, or every copilot query answers 503 `offline`.
Nothing in this section is applied by Terraform yet. There is no kill switch: to take the assistant out of service,
redeploy the previous revision.

| Variable | Value | Notes |
|---|---|---|
| `GOOGLE_GENAI_USE_ENTERPRISE` | `true` | Makes the model client use Vertex AI with the service identity instead of an API key. |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | project id, `global` | The current model generation is served from the `global` endpoint only. |
| `EIOS_GEMINI_MODEL` | model id | Lives in tfvars/config only (ADR-002). |
| `EIOS_PERSISTENCE`, `EIOS_FIRESTORE_DATABASE` | `firestore`, `eios-state` | Conversation sessions. Outside dev/test the service refuses to start without them: an in-memory thread would not survive a revision or be shared across instances. |
| `EIOS_MODEL_ARMOR_PROMPT_TEMPLATE`, `EIOS_MODEL_ARMOR_RESPONSE_TEMPLATE` | full template resource names | Both or neither. Outside dev/test the service refuses to start without both. The templates do not exist yet: they need Terraform, which is not written until approved. If screening fails the turn is blocked, never passed through. |
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

### Dev sandbox measurement (2026-10-14, from a laptop, `us-central1` templates)
- Applied: the API and the two templates (3 resources). No false positive on 27 golden questions `[MEASURED]`; no screening failure; no block on 6 real assistant answers `[MEASURED]`.
- Latency of one screening call from a laptop over the internet: median about 430 ms and p95 about 790 ms after a 2 s cold first call `[MEASURED]`. The pre-registered budget of 400 ms at p95 `[ASSUMPTION]` is **not met from here**; the number that matters is from Cloud Run in the same region and has not been measured. A screened turn took about 1 to 1.5 s longer than an unscreened one `[MEASURED]`.
- Attack questions: 1 of 15 blocked on the prompt side `[MEASURED]`. Model Armor is a content-safety filter, not our access control: write attempts, impersonation, stage-then-approve and cross-scope requests are stopped by the tool port (role scoping, no approve or execute tool) and judged by the spec 022 attack gates.
- Cold start: the first screened turn after a restart took about 12 s `[MEASURED]` because the service connection is opened lazily. The app now warms it in the background at startup (`assistant_gateway.warm_up`); the first turn then took about 6 s `[MEASURED]`.
- Open: re-run `screening_probe` from inside `us-central1` before choosing prod-like thresholds; decide whether Sensitive Data Protection is wanted after reading real traffic.

## Known exceptions
- **Guardrails off** (`enforce_guardrails = false`) in eios-hackathon-prod: the deploying identity lacks
  `orgpolicy.policyAdmin`. Re-enable once granted. [ASSUMPTION: hackathon project]
- **Public invocation** is allowed for cockpit_web only (`allow_public_invocation`); the API stays private.
- **Evidence bucket retention lock** disabled (`evidence_lock_retention = false`) to avoid an irreversible lock.
