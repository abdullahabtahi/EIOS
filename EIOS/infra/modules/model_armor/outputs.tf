output "prompt_template_name" {
  description = "Full resource name for EIOS_MODEL_ARMOR_PROMPT_TEMPLATE."
  value       = google_model_armor_template.prompt.id
}

output "response_template_name" {
  description = "Full resource name for EIOS_MODEL_ARMOR_RESPONSE_TEMPLATE."
  value       = google_model_armor_template.response.id
}

output "location" {
  description = "Region of both templates."
  value       = var.location
}
