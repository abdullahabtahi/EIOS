output "datasets" {
  description = "The datasets created."
  value       = module.bigquery_warm.datasets
}

output "tables" {
  description = "The tables created, as dataset.table."
  value       = module.bigquery_warm.tables
}
