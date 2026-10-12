# stage environment root. Owns its project reference and state prefix; references nothing
# from stage or prod-like. See docs/environments.md for how the three environments differ.

terraform {
  # [SPIKE] The minimum Terraform version and the provider version are not pinned as facts.
  required_version = ">= 1.6"

  required_providers {
    google = {
      source = "hashicorp/google"
      # version = "REPLACE_ME_after_spike" # [SPIKE] unverified until the first reviewed init
    }
  }

  # The bucket is supplied at init time (-backend-config="bucket=<state bucket>") from the
  # bootstrap output. The prefix is fixed here and is unique to this environment.
  backend "gcs" {
    prefix = "envs/stage"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  environment  = "stage"
  state_prefix = "envs/stage"

  # Workload identity federation principals, built from variables only.
  ci_repository_principal = "principalSet://iam.googleapis.com/${var.workload_identity_pool_name}/attribute.repository/${var.ci_repository}"
  release_candidate_principal = join("", [
    "principalSet://iam.googleapis.com/${var.workload_identity_pool_name}/attribute.workflow_ref/",
    "${var.ci_repository}/.github/workflows/release-candidate.yml@${var.release_candidate_git_ref}",
  ])

  runtime_roles = [
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ]
}

locals {
  budgets = yamldecode(file("${path.module}/../../../config/budgets.yaml"))
}

module "budget_alerts" {
  source             = "../../modules/budget_alerts"
  project_id         = var.project_id
  environment        = local.environment
  billing_account    = var.billing_account
  notification_email = var.notification_email
  thresholds_percent = local.budgets.thresholds_percent
  amount             = local.budgets.environments[local.environment].amount
  currency_code      = local.budgets.currency
}

module "project_baseline" {
  source = "../../modules/project_baseline"

  project_id         = var.project_id
  environment        = local.environment
  enforce_guardrails = var.enforce_guardrails
}

# One identity per service; the five names match infra/identities.yaml.
module "identity_skeleton_edge" {
  source = "../../modules/service_identity"

  project_id     = var.project_id
  environment    = local.environment
  service        = "skeleton_edge"
  roles          = local.runtime_roles
  act_as_members = { pipeline = module.identity_pipeline.member }

  depends_on = [module.project_baseline]
}

module "identity_skeleton_core" {
  source = "../../modules/service_identity"

  project_id     = var.project_id
  environment    = local.environment
  service        = "skeleton_core"
  roles          = local.runtime_roles
  act_as_members = { pipeline = module.identity_pipeline.member }

  depends_on = [module.project_baseline]
}

module "identity_pipeline" {
  source = "../../modules/service_identity"

  project_id           = var.project_id
  environment          = local.environment
  service              = "pipeline"
  roles                = ["roles/logging.logWriter", "roles/run.developer"]
  impersonator_members = { ci_repository = local.ci_repository_principal }

  depends_on = [module.project_baseline]
}

module "identity_eval_harness" {
  source = "../../modules/service_identity"

  project_id           = var.project_id
  environment          = local.environment
  service              = "eval_harness"
  roles                = ["roles/logging.logWriter"]
  impersonator_members = { ci_repository = local.ci_repository_principal }

  depends_on = [module.project_baseline]
}

# Reachable only by attribute-restricted impersonation from the release-candidate workflow.
module "identity_release_candidate" {
  source = "../../modules/service_identity"

  project_id                                 = var.project_id
  environment                                = local.environment
  service                                    = "release_candidate"
  roles                                      = ["roles/logging.logWriter"]
  impersonator_members                       = { release_candidate_workflow = local.release_candidate_principal }
  require_attribute_restricted_impersonation = true

  depends_on = [module.project_baseline]
}
