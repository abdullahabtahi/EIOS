output "environment" {
  description = "Environment name."
  value       = local.environment
}

output "state_prefix" {
  description = "State prefix unique to this environment."
  value       = local.state_prefix
}

output "service_account_emails" {
  description = "Service account email per service identity."
  value = {
    skeleton_edge     = module.identity_skeleton_edge.email
    skeleton_core     = module.identity_skeleton_core.email
    pipeline          = module.identity_pipeline.email
    eval_harness      = module.identity_eval_harness.email
    release_candidate = module.identity_release_candidate.email
  }
}

output "eval_truth_bucket" {
  description = "Ground-truth bucket (development and validation splits)."
  value       = module.eval_truth_store.bucket_name
}

output "eval_truth_sealed_bucket" {
  description = "Sealed ground-truth bucket."
  value       = module.eval_truth_store.sealed_bucket_name
}

output "evidence_bucket" {
  description = "Evidence bucket."
  value       = module.evidence_store.bucket_name
}

output "image_repository" {
  description = "Registry path prefix; reference images by digest."
  value       = module.artifact_registry.repository_url
}

output "state_database_id" {
  description = "Firestore database id for gateway counters and replay cache."
  value       = module.state_stores.database_id
}

output "signing_key_enabled" {
  description = "Whether the signing key exists in this environment."
  value       = module.secret_store.signing_key_enabled
}
