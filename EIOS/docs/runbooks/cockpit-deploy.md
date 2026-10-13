# Runbook: deploy the cockpit (web + API)

Two Cloud Run services in the prod-like project: **eios** (the web service; public; the only public entry point; it signs
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

## Known exceptions
- **Guardrails off** (`enforce_guardrails = false`) in eios-hackathon-prod: the deploying identity lacks
  `orgpolicy.policyAdmin`. Re-enable once granted. [ASSUMPTION: hackathon project]
- **Public invocation** is allowed for cockpit_web only (`allow_public_invocation`); the API stays private.
- **Evidence bucket retention lock** disabled (`evidence_lock_retention = false`) to avoid an irreversible lock.
