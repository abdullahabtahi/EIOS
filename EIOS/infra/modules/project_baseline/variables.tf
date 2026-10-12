variable "project_id" {
  description = "Cloud project that this environment owns. Supplied by the environment root; never a literal in the repository."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid cloud project id: lowercase letters, digits and hyphens, starting with a letter."
  }
}

variable "environment" {
  description = "Environment name. One of dev, stage, prod-like."
  type        = string

  validation {
    condition     = contains(["dev", "stage", "prod-like"], var.environment)
    error_message = "environment must be one of dev, stage, prod-like."
  }
}

variable "required_apis" {
  description = "Service APIs that must be enabled before any other module in this environment applies."
  type        = list(string)
  default = [
    "artifactregistry.googleapis.com",
    "cloudkms.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "orgpolicy.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
  ]

  validation {
    condition     = alltrue([for api in var.required_apis : can(regex("^[a-z0-9-]+\\.googleapis\\.com$", api))])
    error_message = "Every entry in required_apis must look like name.googleapis.com."
  }
}

variable "log_retention_days" {
  description = "Retention of the default log bucket in days. The default is an [ASSUMPTION] to be revisited after the first cost reconciliation."
  type        = number
  default     = 30

  validation {
    condition     = var.log_retention_days >= 1 && var.log_retention_days <= 3650 && floor(var.log_retention_days) == var.log_retention_days
    error_message = "log_retention_days must be a whole number between 1 and 3650."
  }
}

variable "data_access_audit_services" {
  description = "Services whose data reads and writes are audit logged. These hold ground truth, evidence, secrets and signing keys."
  type        = list(string)
  default = [
    "cloudkms.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
  ]

  validation {
    condition     = alltrue([for api in var.data_access_audit_services : can(regex("^[a-z0-9-]+\\.googleapis\\.com$", api))])
    error_message = "Every audited service must look like name.googleapis.com."
  }
}

variable "enforce_guardrails" {
  description = "Whether to enforce the project-level guardrail policies. Set false only where the caller cannot manage policies; the exception must be recorded in docs/environments.md."
  type        = bool
  default     = true
}

variable "guardrail_constraints" {
  description = "Boolean policy constraints enforced when enforce_guardrails is true: no service account keys (federation only), uniform bucket access, no public buckets."
  type        = list(string)
  default = [
    "iam.disableServiceAccountKeyCreation",
    "iam.disableServiceAccountKeyUpload",
    "storage.publicAccessPrevention",
    "storage.uniformBucketLevelAccess",
  ]

  validation {
    condition     = alltrue([for c in var.guardrail_constraints : can(regex("^[a-z]+\\.[A-Za-z]+$", c))])
    error_message = "Constraint names are written without the constraints/ prefix, for example iam.disableServiceAccountKeyCreation."
  }
}
