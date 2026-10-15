output "datasets" {
  description = "The dataset ids, one per bounded context."
  value       = sort(tolist(local.datasets))
}

output "tables" {
  description = "Every table as dataset.table."
  value       = sort(keys(local.by_key))
}
