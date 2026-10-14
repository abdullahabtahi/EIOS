# The regulatory knowledge index for the assistant's `search_regulations` capability (Phase 3): a private bucket for
# the corpus files and one Agent Search data store that parses them with the layout parser and chunks them along
# the document's own headings, so every retrieved passage carries its page span and document. The data store is
# global (Agent Search offers global, us and eu); the bucket is regional. No engine is created: the assistant
# queries the data store's default serving config directly, so there is no extra edition to pay for.

terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source = "hashicorp/google"
      # version = "REPLACE_ME_after_spike" # [SPIKE] unverified until the first reviewed init
    }
  }
}

locals {
  bucket_name   = "eios-knowledge-${var.environment}-${var.project_id}"
  data_store_id = "eios-regulations-${var.environment}"
  labels = {
    environment = var.environment
    purpose     = "regulatory-retrieval"
  }
}

resource "google_project_service" "discoveryengine" {
  project            = var.project_id
  service            = "discoveryengine.googleapis.com"
  disable_on_destroy = false
}

# The corpus as acquired (regulator PDFs). Private; public access is blocked. Versioning keeps a replaced file
# recoverable, and the ingestion script verifies each file's sha256 against data/corpus/regulatory/manifest.yaml.
resource "google_storage_bucket" "corpus" {
  project                     = var.project_id
  name                        = local.bucket_name
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels

  versioning {
    enabled = true
  }
}

resource "google_discovery_engine_data_store" "regulations" {
  project           = var.project_id
  location          = "global"
  data_store_id     = local.data_store_id
  display_name      = "EIOS regulatory corpus (${var.environment})"
  industry_vertical = "GENERIC"
  content_config    = "CONTENT_REQUIRED"
  solution_types    = ["SOLUTION_TYPE_SEARCH"]

  # Layout-aware chunking cannot be turned on or off after creation, so it is set here and never edited.
  document_processing_config {
    chunking_config {
      layout_based_chunking_config {
        chunk_size                = var.chunk_size_tokens
        include_ancestor_headings = true
      }
    }
    default_parsing_config {
      layout_parsing_config {}
    }
  }

  depends_on = [google_project_service.discoveryengine]
}

# Who may query the index (the assistant's identity, or a person for local runs). Search only; no write.
resource "google_project_iam_member" "searchers" {
  for_each = toset(var.search_members)
  project  = var.project_id
  role     = "roles/discoveryengine.viewer"
  member   = each.value
}

# Who may load documents (the ingestion script run by the operator or the pipeline identity).
resource "google_project_iam_member" "editors" {
  for_each = toset(var.ingest_members)
  project  = var.project_id
  role     = "roles/discoveryengine.editor"
  member   = each.value
}

resource "google_storage_bucket_iam_member" "corpus_writers" {
  for_each = toset(var.ingest_members)
  bucket   = google_storage_bucket.corpus.name
  role     = "roles/storage.objectAdmin"
  member   = each.value
}
