# One service account per service, with an explicit declared role list.
# Roles listed here are project level. Resource-level access (buckets, secrets, registry,
# Firestore) is granted by the store modules, so that it stays scoped to one resource.

terraform {
  # [SPIKE] The minimum Terraform version and the provider version are not pinned as facts.
  required_version = ">= 1.6"

  required_providers {
    google = {
      source = "hashicorp/google"
      # version = "REPLACE_ME_after_spike" # [SPIKE] unverified until the first reviewed init
    }
  }
}

locals {
  account_id = replace(var.service, "_", "-")
}

resource "google_service_account" "this" {
  project      = var.project_id
  account_id   = local.account_id
  display_name = "${var.service} (${var.environment})"
  description  = var.description

  lifecycle {
    precondition {
      condition = (
        !var.require_attribute_restricted_impersonation ||
        (
          length(var.impersonator_members) > 0 &&
          alltrue([
            for m in values(var.impersonator_members) :
            can(regex("^principalSet://iam\\.googleapis\\.com/.+/attribute\\.[A-Za-z_]+/.+$", m))
          ])
        )
      )
      error_message = "This identity requires attribute-restricted impersonation: impersonator_members must be non-empty and every entry must be a principalSet scoped to one attribute value."
    }
  }
}

resource "google_project_iam_member" "role" {
  for_each = toset(var.roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.this.email}"
}

# Who may mint tokens for this identity (workload identity federation principals).
resource "google_service_account_iam_member" "impersonator" {
  for_each = var.impersonator_members

  service_account_id = google_service_account.this.name
  role               = "roles/iam.workloadIdentityUser"
  member             = each.value
}

# Who may attach this identity to a deployed service (deploy-time act-as, on this identity only).
resource "google_service_account_iam_member" "act_as" {
  for_each = var.act_as_members

  service_account_id = google_service_account.this.name
  role               = "roles/iam.serviceAccountUser"
  member             = each.value
}
