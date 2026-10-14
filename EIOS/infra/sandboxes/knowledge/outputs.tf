output "data_store_id" {
  description = "Set EIOS_KNOWLEDGE_DATA_STORE to this when running the gateway locally."
  value       = module.knowledge.data_store_id
}

output "corpus_bucket" {
  description = "Bucket the ingestion script uploads the corpus to."
  value       = module.knowledge.corpus_bucket
}
