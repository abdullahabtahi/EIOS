output "data_store_id" {
  description = "Set EIOS_KNOWLEDGE_DATA_STORE to this when running the gateway or the ingestion script."
  value       = google_discovery_engine_data_store.regulations.data_store_id
}

output "data_store_name" {
  description = "Full resource name of the data store."
  value       = google_discovery_engine_data_store.regulations.name
}

output "corpus_bucket" {
  description = "Bucket the ingestion script uploads the corpus files to."
  value       = google_storage_bucket.corpus.name
}
