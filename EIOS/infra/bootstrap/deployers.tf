# One deployer identity per environment, living in that environment's project and holding
# only the roles in var.deployer_roles there. It can be impersonated only by CI jobs of the
# allowed repository that run under the GitHub environment of the same name.
locals {
  pool_name = google_iam_workload_identity_pool.ci.name

  deployer_role_bindings = {
    for pair in setproduct(keys(var.environment_project_ids), var.deployer_roles) :
    "${pair[0]}/${pair[1]}" => { environment = pair[0], role = pair[1] }
  }
}

resource "google_service_account" "deployer" {
  for_each = var.environment_project_ids

  project      = google_project.environment[each.key].project_id
  account_id   = "eios-deployer"
  display_name = "Terraform deployer (${each.key})"
  description  = "Applies infra/envs/${each.key} from CI. Impersonated through federation only."

  depends_on = [google_project_service.environment]
}

resource "google_project_iam_member" "deployer" {
  for_each = local.deployer_role_bindings

  project = google_project.environment[each.value.environment].project_id
  role    = each.value.role
  member  = google_service_account.deployer[each.value.environment].member
}

resource "google_service_account_iam_member" "deployer_impersonation" {
  for_each = var.environment_project_ids

  service_account_id = google_service_account.deployer[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${local.pool_name}/attribute.environment/${each.key}"
}

# State access: each deployer reaches only its own prefix. The condition is a name-prefix
# match on object names. Behaviour of listing under this condition is unverified without
# a cloud account (see docs/runbooks/bootstrap.md, "What is not verified").
resource "google_storage_bucket_iam_member" "deployer_state" {
  for_each = var.environment_project_ids

  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectUser"
  member = google_service_account.deployer[each.key].member

  condition {
    title       = "state-prefix-${each.key}"
    description = "Only objects under envs/${each.key}/ in the state bucket."
    expression  = "resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.state.name}/objects/envs/${each.key}/\")"
  }
}
