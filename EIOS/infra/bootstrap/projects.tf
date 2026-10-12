locals {
  # Mark which environments exist; labels carry no secrets.
  control_labels = { purpose = "terraform-control", managed-by = "terraform" }

  control_apis = [
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ]
}

resource "google_project" "control" {
  name            = var.control_project_id
  project_id      = var.control_project_id
  org_id          = var.parent_org_id
  folder_id       = var.parent_folder_id
  billing_account = var.billing_account_id
  labels          = local.control_labels

  # Cloud projects are not destroyed by accident.
  deletion_policy = "PREVENT"

  lifecycle {
    precondition {
      condition     = (var.parent_org_id == null) != (var.parent_folder_id == null)
      error_message = "Set exactly one of parent_org_id and parent_folder_id."
    }
  }
}

resource "google_project_service" "control" {
  for_each = toset(local.control_apis)

  project            = google_project.control.project_id
  service            = each.value
  disable_on_destroy = false
}

# One isolated project per environment. [ASSUMPTION] see docs/environments.md.
resource "google_project" "environment" {
  for_each = var.environment_project_ids

  name            = each.value
  project_id      = each.value
  org_id          = var.parent_org_id
  folder_id       = var.parent_folder_id
  billing_account = var.billing_account_id
  labels          = { environment = each.key, managed-by = "terraform" }

  deletion_policy = "PREVENT"
}

resource "google_project_service" "environment" {
  for_each = {
    for pair in setproduct(keys(var.environment_project_ids), var.bootstrap_apis) :
    "${pair[0]}/${pair[1]}" => { environment = pair[0], api = pair[1] }
  }

  project            = google_project.environment[each.value.environment].project_id
  service            = each.value.api
  disable_on_destroy = false
}
