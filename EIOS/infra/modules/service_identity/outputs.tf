output "service" {
  description = "Service name this identity belongs to."
  value       = var.service
}

output "email" {
  description = "Service account email."
  value       = google_service_account.this.email
}

output "member" {
  description = "IAM member string (serviceAccount:email) for use in resource-level grants."
  value       = "serviceAccount:${google_service_account.this.email}"
}

output "name" {
  description = "Fully qualified service account resource name."
  value       = google_service_account.this.name
}

output "roles" {
  description = "Project-level roles granted to this identity."
  value       = sort(var.roles)
}
