# CI identity federation (GitHub OIDC). Restricted to one repository: the provider rejects
# any token whose repository claim differs, so a fork or another repository cannot even
# exchange a token, regardless of IAM bindings elsewhere.
resource "google_iam_workload_identity_pool" "ci" {
  project                   = google_project.control.project_id
  workload_identity_pool_id = "eios-ci"
  display_name              = "EIOS CI federation"
  description               = "Federation for GitHub Actions of one repository. No long-lived keys."

  depends_on = [google_project_service.control]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = google_project.control.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.ci.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions"
  display_name                       = "GitHub Actions"

  attribute_mapping = {
    "google.subject"         = "assertion.sub"
    "attribute.repository"   = "assertion.repository"
    "attribute.workflow_ref" = "assertion.workflow_ref"
    "attribute.environment"  = "assertion.environment"
    "attribute.ref"          = "assertion.ref"
  }

  attribute_condition = "assertion.repository == \"${var.ci_repository}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}
