# Model Armor templates in the dev sandbox project, applied on their own so the assistant can be screened and
# measured locally before prod-like gets the same module. This root owns only the templates: the full dev
# environment (envs/dev) is a separate, unapplied skeleton and is not touched. State prefix is unique to this root.

terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source = "hashicorp/google"
      # version = "REPLACE_ME_after_spike" # [SPIKE] unverified until the first reviewed init
    }
  }

  # The bucket is supplied at init time: terraform init -backend-config=bucket=eios-tfstate-eios-hackathon
  backend "gcs" {
    prefix = "sandboxes/model-armor"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "model_armor" {
  source = "../../modules/model_armor"

  project_id  = var.project_id
  environment = "dev"
  location    = var.region

  # Tuning on synthetic data only: log each screening call so thresholds can be read from real matches.
  log_sanitize_operations = true
  sanitize_members        = var.sanitize_members
}
