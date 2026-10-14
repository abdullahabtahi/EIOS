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

## ADK assistant (flag `EIOS_ASSISTANT_RUNTIME`)
The cockpit's copilot endpoint is served by one of two runtimes. `legacy` (default) is the old copilot. `adk` is the ADK
assistant (`src/eios/assistant/`, ADR-019). Nothing in this section is applied by Terraform yet; set these on the
`eios-api` Cloud Run service only when the rollout gate has passed (`evals/agent/thresholds.yaml`, `docs/agent-baseline.md`).

| Variable | Value | Notes |
|---|---|---|
| `EIOS_ASSISTANT_RUNTIME` | `legacy` or `adk` | Per environment. **Kill switch: set it back to `legacy`** and redeploy the revision; no code change. Any other value makes the endpoint answer 503 `offline`. |
| `GOOGLE_GENAI_USE_ENTERPRISE` | `true` | Makes the Gemini client use Vertex AI with the service identity instead of an API key. |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | project id, `global` | Gemini 3.x is served from the `global` endpoint only. |
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

## Known exceptions
- **Guardrails off** (`enforce_guardrails = false`) in eios-hackathon-prod: the deploying identity lacks
  `orgpolicy.policyAdmin`. Re-enable once granted. [ASSUMPTION: hackathon project]
- **Public invocation** is allowed for cockpit_web only (`allow_public_invocation`); the API stays private.
- **Evidence bucket retention lock** disabled (`evidence_lock_retention = false`) to avoid an irreversible lock.
