# The regulatory knowledge index in the dev sandbox project, applied on its own so retrieval can be built and measured
# locally before prod-like gets the same module. This root owns only the index and its bucket; it shares no state with
# the Model Armor sandbox or the dev environment skeleton. State prefix is unique to this root.

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
    prefix = "sandboxes/knowledge"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "knowledge" {
  source = "../../modules/knowledge"

  project_id     = var.project_id
  environment    = "dev"
  location       = var.region
  search_members = var.search_members
  ingest_members = var.ingest_members
}
