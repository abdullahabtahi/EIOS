# Restricted buckets for evaluation ground truth (Constitution VI, FR-019).
# Two buckets: the development and validation splits, readable only by the harness and
# pipeline identities, and the sealed split, readable only by the release-candidate identity.
# No runtime service identity appears here and none may be passed in.

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

resource "google_storage_bucket" "truth" {
  name                        = "${var.project_id}-${var.bucket_name_suffix}"
  project                     = var.project_id
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  labels = {
    environment = var.environment
    purpose     = "eval-truth"
  }
}

resource "google_storage_bucket" "sealed" {
  name                        = "${var.project_id}-${var.bucket_name_suffix}-sealed"
  project                     = var.project_id
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  labels = {
    environment = var.environment
    purpose     = "eval-truth-sealed"
  }
}

# Read access: harness and pipeline identities only.
resource "google_storage_bucket_iam_member" "reader" {
  for_each = var.reader_members

  bucket = google_storage_bucket.truth.name
  role   = "roles/storage.objectViewer"
  member = each.value
}

# Sealed split: the release-candidate identity only. That identity is itself reachable only
# by attribute-restricted impersonation from the release-candidate workflow (service_identity).
resource "google_storage_bucket_iam_member" "sealed_reader" {
  for_each = var.sealed_reader_members

  bucket = google_storage_bucket.sealed.name
  role   = "roles/storage.objectViewer"
  member = each.value
}
