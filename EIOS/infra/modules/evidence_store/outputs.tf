output "bucket_name" {
  description = "Evidence bucket name."
  value       = google_storage_bucket.evidence.name
}

output "retention_locked" {
  description = "Whether the retention policy is locked."
  value       = var.lock_retention
}

output "retention_days" {
  description = "Retention period in days."
  value       = var.retention_days
}
