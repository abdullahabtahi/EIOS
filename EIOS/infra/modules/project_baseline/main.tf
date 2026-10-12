# Project baseline: required APIs, log retention, audit logging, guardrail policies.
# Called by every environment root (infra/envs/*).

terraform {
  # [SPIKE] The minimum Terraform version and the provider version are not pinned as facts.
  # Pin them after the first reviewed init and record the result in docs/conventions.md.
  required_version = ">= 1.6"

  required_providers {
    google = {
      source = "hashicorp/google"
      # version = "REPLACE_ME_after_spike" # [SPIKE] unverified until the first reviewed init
    }
  }
}

resource "google_project_service" "required" {
  for_each = toset(var.required_apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Log retention for the default bucket. The number is a variable, not a literal.
resource "google_logging_project_bucket_config" "default" {
  project        = var.project_id
  location       = "global"
  bucket_id      = "_Default"
  retention_days = var.log_retention_days

  depends_on = [google_project_service.required]
}

# Administrative reads are audited everywhere; data access is audited for the stores
# that hold evidence, secrets, signing keys and ground truth.
resource "google_project_iam_audit_config" "all_services" {
  project = var.project_id
  service = "allServices"

  audit_log_config {
    log_type = "ADMIN_READ"
  }

  depends_on = [google_project_service.required]
}

resource "google_project_iam_audit_config" "data_access" {
  for_each = toset(var.data_access_audit_services)

  project = var.project_id
  service = each.value

  audit_log_config {
    log_type = "DATA_READ"
  }

  audit_log_config {
    log_type = "DATA_WRITE"
  }

  depends_on = [google_project_service.required]
}

# Guardrails in the style of organisation policy, applied at project level.
# Needs a caller allowed to set project policies (documented in docs/runbooks/bootstrap.md).
resource "google_org_policy_policy" "guardrail" {
  for_each = var.enforce_guardrails ? toset(var.guardrail_constraints) : toset([])

  name   = "projects/${var.project_id}/policies/${each.value}"
  parent = "projects/${var.project_id}"

  spec {
    rules {
      enforce = "TRUE"
    }
  }

  depends_on = [google_project_service.required]
}
