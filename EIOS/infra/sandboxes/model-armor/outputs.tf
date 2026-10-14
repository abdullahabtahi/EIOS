output "prompt_template_name" {
  description = "Set EIOS_MODEL_ARMOR_PROMPT_TEMPLATE to this when running the gateway locally."
  value       = module.model_armor.prompt_template_name
}

output "response_template_name" {
  description = "Set EIOS_MODEL_ARMOR_RESPONSE_TEMPLATE to this when running the gateway locally."
  value       = module.model_armor.response_template_name
}
