# Retention-locked bucket for pipeline run records and evidence (FR-009, FR-010).

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

resource "google_storage_bucket" "evidence" {
  name                        = "${var.project_id}-${var.bucket_name_suffix}"
  project                     = var.project_id
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  # A locked retention policy cannot be shortened or removed (irreversible).
  retention_policy {
    retention_period = var.retention_days * 86400
    is_locked        = var.lock_retention
  }

  labels = {
    environment = var.environment
    purpose     = "evidence"
  }
}

# Writers create objects but cannot read or overwrite them.
resource "google_storage_bucket_iam_member" "writer" {
  for_each = var.writer_members

  bucket = google_storage_bucket.evidence.name
  role   = "roles/storage.objectCreator"
  member = each.value
}

resource "google_storage_bucket_iam_member" "reader" {
  for_each = var.reader_members

  bucket = google_storage_bucket.evidence.name
  role   = "roles/storage.objectViewer"
  member = each.value
}
