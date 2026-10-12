# Firestore database for gateway token counters and the replay cache (used by the gateway
# store in src/eios/llm_gateway/stores/firestore.py). One named database per environment
# project, so nothing is shared across environments.

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

resource "google_firestore_database" "state" {
  project                 = var.project_id
  name                    = var.database_id
  location_id             = var.location_id
  type                    = "FIRESTORE_NATIVE"
  delete_protection_state = var.deletion_protection ? "DELETE_PROTECTION_ENABLED" : "DELETE_PROTECTION_DISABLED"
}

# Replay entries expire: documents carry an expires_at timestamp and are removed by TTL.
resource "google_firestore_field" "replay_ttl" {
  project    = var.project_id
  database   = google_firestore_database.state.name
  collection = var.replay_collection
  field      = "expires_at"

  ttl_config {}
}

# Data access limited to this database, for the services that use the gateway stores.
resource "google_project_iam_member" "user" {
  for_each = var.user_members

  project = var.project_id
  role    = "roles/datastore.user"
  member  = each.value

  condition {
    title       = "only_${var.database_id}"
    description = "Limits access to the ${var.database_id} database."
    expression  = "resource.name == \"projects/${var.project_id}/databases/${var.database_id}\""
  }
}
