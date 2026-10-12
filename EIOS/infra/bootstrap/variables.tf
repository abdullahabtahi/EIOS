variable "region" {
  description = "Region for the state bucket."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]+$", var.region))
    error_message = "region must be a lowercase region name."
  }
}

variable "billing_account_id" {
  description = "Billing account attached to every project this root creates."
  type        = string

  validation {
    condition     = can(regex("^[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$", var.billing_account_id))
    error_message = "billing_account_id must look like XXXXXX-XXXXXX-XXXXXX."
  }
}

variable "parent_org_id" {
  description = "Numeric organisation id that owns the projects. Set exactly one of parent_org_id and parent_folder_id."
  type        = string
  default     = null

  validation {
    condition     = var.parent_org_id == null || can(regex("^[0-9]+$", var.parent_org_id))
    error_message = "parent_org_id must be numeric."
  }
}

variable "parent_folder_id" {
  description = "Numeric folder id that owns the projects. Set exactly one of parent_org_id and parent_folder_id."
  type        = string
  default     = null

  validation {
    condition     = var.parent_folder_id == null || can(regex("^[0-9]+$", var.parent_folder_id))
    error_message = "parent_folder_id must be numeric."
  }
}

variable "control_project_id" {
  description = "Project that holds the state bucket and the federation pool. Must be globally unique."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.control_project_id))
    error_message = "control_project_id must be a valid project id."
  }
}

variable "environment_project_ids" {
  description = "Project id per environment. [ASSUMPTION] one isolated project per environment; keys must be exactly dev, stage and prod-like, values must be distinct."
  type        = map(string)

  validation {
    condition     = toset(keys(var.environment_project_ids)) == toset(["dev", "stage", "prod-like"])
    error_message = "environment_project_ids must have exactly the keys dev, stage and prod-like."
  }

  validation {
    condition     = length(toset(values(var.environment_project_ids))) == 3
    error_message = "Each environment must use its own project id; sharing a project between environments is not allowed."
  }

  validation {
    condition     = alltrue([for env, id in var.environment_project_ids : can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", id))])
    error_message = "Every project id must be a valid project id."
  }
}

variable "ci_repository" {
  description = "The only repository allowed to authenticate through federation, as owner/name."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.ci_repository))
    error_message = "ci_repository must be written as owner/name."
  }
}

variable "state_noncurrent_retention_days" {
  description = "Days to keep superseded state object versions. [ASSUMPTION] 90."
  type        = number
  default     = 90

  validation {
    condition     = var.state_noncurrent_retention_days >= 7 && floor(var.state_noncurrent_retention_days) == var.state_noncurrent_retention_days
    error_message = "state_noncurrent_retention_days must be a whole number of at least 7."
  }
}

variable "deployer_roles" {
  description = "Roles each environment deployer holds in its own project. Basic roles and wildcards are rejected."
  type        = list(string)
  default = [
    "roles/artifactregistry.admin",
    "roles/cloudkms.admin",
    "roles/datastore.owner",
    "roles/iam.serviceAccountAdmin",
    "roles/logging.admin",
    "roles/orgpolicy.policyAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/secretmanager.admin",
    "roles/serviceusage.serviceUsageAdmin",
    "roles/storage.admin",
  ]

  validation {
    condition     = length(var.deployer_roles) > 0
    error_message = "deployer_roles must not be empty."
  }

  validation {
    condition     = alltrue([for r in var.deployer_roles : !can(regex("[*?]", r))])
    error_message = "Wildcards are not allowed in deployer_roles."
  }

  validation {
    condition     = alltrue([for r in var.deployer_roles : !contains(["roles/owner", "roles/editor"], r)])
    error_message = "roles/owner and roles/editor are not allowed in deployer_roles."
  }

  validation {
    condition     = alltrue([for r in var.deployer_roles : can(regex("^(roles/[A-Za-z0-9_.]+|organizations/[0-9]+/roles/[A-Za-z0-9_.]+|projects/[a-z0-9-]+/roles/[A-Za-z0-9_.]+)$", r))])
    error_message = "Each role must be a role name such as roles/run.admin."
  }
}

variable "bootstrap_apis" {
  description = "APIs enabled in each environment project so that the deployer can manage the rest."
  type        = list(string)
  default = [
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "serviceusage.googleapis.com",
  ]

  validation {
    condition     = alltrue([for a in var.bootstrap_apis : can(regex("^[a-z0-9-]+\\.googleapis\\.com$", a))])
    error_message = "Each API must look like name.googleapis.com."
  }
}
