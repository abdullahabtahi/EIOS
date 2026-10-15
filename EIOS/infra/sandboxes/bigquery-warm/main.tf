# The warm tier in the dev sandbox project, applied on its own so the pipeline can be built and measured there before
# prod-like gets the same module. This root owns only the datasets and tables. State prefix is unique to this root.

terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }

  # The bucket is supplied at init time: terraform init -backend-config=bucket=eios-tfstate-eios-hackathon
  backend "gcs" {
    prefix = "sandboxes/bigquery-warm"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "bigquery_warm" {
  source = "../../modules/bigquery_warm"

  project_id     = var.project_id
  environment    = "dev"
  location       = var.region
  reader_members = var.reader_members
  writer_members = var.writer_members
}
