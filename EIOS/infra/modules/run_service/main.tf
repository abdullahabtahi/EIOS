# Cloud Run service wiring. The service runs as its own identity (created by the
# service_identity module and passed in), pulls its image by digest, and is invoked
# only by explicitly listed members. min_instances is an explicit variable (FR-015).

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

resource "google_cloud_run_v2_service" "this" {
  project             = var.project_id
  name                = replace(var.service, "_", "-")
  location            = var.region
  ingress             = var.ingress
  deletion_protection = var.deletion_protection

  labels = {
    environment = var.environment
    stateful    = tostring(var.stateful)
  }

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret_id
              version = env.value.version
            }
          }
        }
      }
    }
  }

  lifecycle {
    precondition {
      condition     = var.max_instances >= var.min_instances
      error_message = "max_instances must be at least min_instances."
    }
    precondition {
      condition     = !(var.stateful && var.warm_start_required) || var.min_instances >= 1
      error_message = "A stateful service in an environment that requires warm start must set min_instances to at least 1."
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "invoker" {
  for_each = var.invoker_members

  project  = var.project_id
  location = google_cloud_run_v2_service.this.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = each.value
}
