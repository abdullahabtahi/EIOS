output "name" {
  description = "Cloud Run service name."
  value       = google_cloud_run_v2_service.this.name
}

output "uri" {
  description = "Service URL."
  value       = google_cloud_run_v2_service.this.uri
}

output "service_account_email" {
  description = "Identity the service runs as."
  value       = var.service_account_email
}

output "min_instances" {
  description = "Configured minimum instances."
  value       = var.min_instances
}

output "image" {
  description = "Image digest reference the service runs."
  value       = var.image
}
