# One-time bootstrap root. It is the single documented manual exception (research R-05):
# a human with elevated rights applies it once with local state, then migrates its state
# into the bucket it creates. Everything after that runs through CI identity federation.
# See docs/runbooks/bootstrap.md for the exact steps.

terraform {
  # [SPIKE] The minimum Terraform version and the provider version are not pinned as facts.
  required_version = ">= 1.6"

  required_providers {
    google = {
      source = "hashicorp/google"
      # version = "REPLACE_ME_after_spike" # [SPIKE] unverified until the first reviewed init
    }
  }

  # No backend block on purpose: the first apply uses local state because the state bucket
  # does not exist yet. After that apply, copy backend.tf.example to backend.tf and migrate.
}

# Credentials come from the operator's own application default credentials. Nothing is
# configured here and no key file is ever created or read.
provider "google" {
  region = var.region
}
