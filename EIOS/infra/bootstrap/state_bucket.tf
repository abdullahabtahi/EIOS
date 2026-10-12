# Remote state: one versioned bucket, one prefix per environment (plus "bootstrap").
resource "google_storage_bucket" "state" {
  name                        = "${google_project.control.project_id}-tfstate"
  project                     = google_project.control.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.control_labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      days_since_noncurrent_time = var.state_noncurrent_retention_days
      with_state                 = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.control]
}
