output "repository_id" {
  description = "Repository id."
  value       = google_artifact_registry_repository.images.repository_id
}

output "repository_url" {
  description = "Registry path prefix. Reference images as <repository_url>/<image>@sha256:<digest>; run_service rejects any other form."
  value       = "${var.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "immutable_tags" {
  description = "Whether tags in this repository are immutable."
  value       = google_artifact_registry_repository.images.docker_config[0].immutable_tags
}
