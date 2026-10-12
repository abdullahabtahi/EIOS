output "state_bucket_name" {
  description = "State bucket. Pass to terraform init as -backend-config=\"bucket=<value>\"."
  value       = google_storage_bucket.state.name
}

output "state_prefixes" {
  description = "State prefix per environment, plus the bootstrap root itself."
  value       = merge({ for env in keys(var.environment_project_ids) : env => "envs/${env}" }, { bootstrap = "bootstrap" })
}

output "workload_identity_pool_name" {
  description = "Full pool name; use as workload_identity_pool_name in each environment root."
  value       = google_iam_workload_identity_pool.ci.name
}

output "workload_identity_provider_name" {
  description = "Full provider name for the CI auth step (workload_identity_provider)."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account_emails" {
  description = "Deployer service account email per environment, for the CI auth step."
  value       = { for env, sa in google_service_account.deployer : env => sa.email }
}

output "environment_project_ids" {
  description = "Project id per environment, echoed for use in each environment tfvars."
  value       = { for env, p in google_project.environment : env => p.project_id }
}
