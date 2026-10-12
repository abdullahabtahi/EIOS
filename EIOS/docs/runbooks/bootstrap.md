# Runbook: one-time bootstrap (T076, research R-05)

**Audience**: a human with elevated rights (organisation or folder administrator plus billing administrator). **Root**: `infra/bootstrap/`.

This is the single documented exception to "nothing is created by hand" (FR-013). The pipeline cannot create the state bucket or the CI identity it depends on, so one person applies this root once, from a workstation, with local state. After the state is migrated into the bucket it creates, every later change goes through CI.

No credentials are written to the repository. The operator uses their own application default credentials; no key file is created, read or stored.

## What it creates

| Resource | Purpose |
|---|---|
| Control project | Holds the state bucket and the federation pool. |
| One project per environment (dev, stage, prod-like) `[ASSUMPTION]` | Isolation boundary; see `docs/environments.md`. |
| State bucket (versioned, uniform access, public access prevented) | Remote state. One prefix per environment (`envs/dev`, `envs/stage`, `envs/prod-like`) plus `bootstrap`. |
| Workload identity pool and GitHub provider | CI authentication without keys. The provider rejects any token whose repository claim is not the configured repository. |
| `eios-deployer` service account in each environment project | The identity CI impersonates to apply that environment. Holds the roles in `var.deployer_roles` in its own project only; no basic roles. |
| Impersonation bindings | Each deployer is impersonable only by CI jobs of the allowed repository running under the GitHub environment of the same name. |
| Prefix-scoped state access | Each deployer can use only its own state prefix. |

## Prerequisites

You need all of these before step 1. They are external to this repository.

1. A **billing account** you may attach projects to (billing administrator).
2. A **parent organisation or folder** where you may create projects (project creator). Set exactly one of `parent_org_id` and `parent_folder_id`.
3. Four unused, globally unique project ids: control, dev, stage, prod-like.
4. The CI repository as `owner/name`.
5. Local tools: Terraform `>= 1.6` `[ASSUMPTION]` and the cloud command-line tool, signed in with `gcloud auth application-default login` as the elevated human.
6. Network access to download the provider.

## Steps

1. Create the variable file. From `infra/bootstrap/` copy `terraform.tfvars.example` to `terraform.tfvars` and replace every `REPLACE_ME_*` value. `terraform.tfvars` is git-ignored and covered by `.terraformignore`; never commit it.
2. Initialise with local state: `terraform init`.
3. Review: `terraform plan -out=bootstrap.tfplan`. Check that exactly 4 projects, one bucket, one pool, one provider, three deployers and their bindings are planned, and nothing is destroyed.
4. Apply once: `terraform apply bootstrap.tfplan`. Delete `bootstrap.tfplan` afterwards (plans can embed resolved values).
5. Record the outputs: `terraform output`. You need `state_bucket_name`, `workload_identity_pool_name`, `workload_identity_provider_name` and `deployer_service_account_emails`.
6. Migrate state into the new bucket: copy `backend.tf.example` to `backend.tf`, then run `terraform init -migrate-state -backend-config="bucket=<state_bucket_name>"` and answer yes. Confirm with `terraform plan` (no changes), then delete the local `terraform.tfstate*` files.
7. Wire CI. In the repository settings create GitHub environments named `dev`, `stage` and `prod-like` (the last with required reviewers). In the workflows, authenticate with the provider and deployer values from step 5 (repository variables, not secrets: they are identifiers, not credentials).
8. Prepare each environment root: in `infra/envs/<env>/` copy `terraform.tfvars.example` to `terraform.tfvars`, set `project_id` to the matching `environment_project_ids` output, `workload_identity_pool_name` to the pool output and `ci_repository` to the repository. Then `terraform init -backend-config="bucket=<state_bucket_name>"`.
9. From this point CI applies the environments. Nobody applies from a workstation again, except to repair this root.

## Rotation and repair

- The pool has no secrets to rotate. To change the allowed repository, change `ci_repository` and apply this root again as the elevated human.
- Deployer roles change only through `var.deployer_roles` in this root, reviewed like any other change.
- Never apply with force-destroy or remove `prevent_destroy` on the state bucket or `deletion_policy` on the projects. If you must, treat it as a new bootstrap.

## What is not verified without a cloud account

This tree was validated statically (`terraform fmt -check`, `terraform validate`, the repository's infra checks). These points need a real run and are `[ASSUMPTION]` (owner: platform engineer, verify by the first real bootstrap run) until one has happened:

- Project creation, billing attachment and the exact permissions the operator needs.
- Whether `roles/orgpolicy.policyAdmin` can be granted on a project. If not, the environment roots cannot apply their guardrail policies; set `enforce_guardrails = false` there and apply the policies at folder level as the elevated human.
- Federation claim mapping (`assertion.environment`, `assertion.workflow_ref`) against a real workflow run.
- Whether listing state objects works under the prefix-conditioned grant on the state bucket.
- Provider version: no version is pinned yet. After the first reviewed `init`, pin it and commit the lock files.
