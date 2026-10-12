output "project_id" {
  description = "Project that the baseline was applied to."
  value       = var.project_id
}

output "environment" {
  description = "Environment name the baseline was applied for."
  value       = var.environment
}

output "enabled_apis" {
  description = "Service APIs enabled by this module."
  value       = sort([for s in google_project_service.required : s.service])
}

output "enforced_guardrails" {
  description = "Guardrail constraints enforced on the project (empty when enforce_guardrails is false)."
  value       = sort([for g in google_org_policy_policy.guardrail : g.name])
}
