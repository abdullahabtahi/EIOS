# Managed secret store (containers only, never values) and an optional signing key.
# The key ring and asymmetric signing key exist only when signing_key_enabled is true
# (prod-like). This key ring extends plan.md; see docs/conventions.md.

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
  secret_accessors = merge([
    for secret_id, spec in var.secrets : {
      for label, member in spec.accessors : "${secret_id}/${label}" => {
        secret_id = secret_id
        member    = member
      }
    }
  ]...)
}

# Secret containers. Values are added out of band and read at run time through the
# reading service's own identity, so rotating a value needs no code change (FR-017).
resource "google_secret_manager_secret" "this" {
  for_each = var.secrets

  project   = var.project_id
  secret_id = each.key
  labels = {
    environment = var.environment
    purpose     = "runtime-secret"
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = local.secret_accessors

  project   = var.project_id
  secret_id = google_secret_manager_secret.this[each.value.secret_id].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = each.value.member
}

resource "terraform_data" "signing_guard" {
  lifecycle {
    precondition {
      condition     = var.signing_key_enabled || (length(var.signer_members) == 0 && length(var.verifier_members) == 0)
      error_message = "signer_members and verifier_members need signing_key_enabled = true."
    }
    precondition {
      condition     = !var.signing_key_enabled || var.kms_location != null
      error_message = "kms_location is required when signing_key_enabled is true."
    }
  }
}

resource "google_kms_key_ring" "signing" {
  count = var.signing_key_enabled ? 1 : 0

  project  = var.project_id
  name     = var.key_ring_name
  location = var.kms_location

  depends_on = [terraform_data.signing_guard]
}

# Asymmetric ECDSA P-256 signing key for Action Intent tokens (invariant 5).
# Asymmetric keys have no automatic rotation: rotate by creating a new version.
resource "google_kms_crypto_key" "signing" {
  count = var.signing_key_enabled ? 1 : 0

  name     = var.signing_key_name
  key_ring = google_kms_key_ring.signing[0].id
  purpose  = "ASYMMETRIC_SIGN"

  version_template {
    algorithm        = "EC_SIGN_P256_SHA256"
    protection_level = var.signing_key_protection_level
  }

  labels = {
    environment = var.environment
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key_iam_member" "signer" {
  for_each = var.signing_key_enabled ? var.signer_members : {}

  crypto_key_id = google_kms_crypto_key.signing[0].id
  role          = "roles/cloudkms.signer"
  member        = each.value
}

resource "google_kms_crypto_key_iam_member" "verifier" {
  for_each = var.signing_key_enabled ? var.verifier_members : {}

  crypto_key_id = google_kms_crypto_key.signing[0].id
  role          = "roles/cloudkms.publicKeyViewer"
  member        = each.value
}
