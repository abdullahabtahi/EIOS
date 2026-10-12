variable "project_id" {
  description = "Cloud project that owns the service account. Supplied by the environment root."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid cloud project id."
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

variable "service" {
  description = "Service name as written in infra/identities.yaml (for example skeleton_edge). One identity per service; never shared."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]{3,28}$", var.service))
    error_message = "service must be lowercase letters, digits and underscores, 4 to 29 characters, starting with a letter."
  }
}

variable "description" {
  description = "Human-readable purpose of the identity."
  type        = string
  default     = "Per-service identity; roles are declared in the environment root and mirrored in infra/identities.yaml."
}

variable "roles" {
  description = "Explicit, non-empty list of project-level roles. Wildcards, the owner role and the project-wide editor role are rejected."
  type        = list(string)

  validation {
    condition     = length(var.roles) > 0
    error_message = "roles must list at least one role explicitly."
  }

  validation {
    condition     = alltrue([for r in var.roles : !can(regex("[*?]", r))])
    error_message = "Wildcard roles are not allowed. List each role explicitly."
  }

  validation {
    condition = alltrue([
      for r in var.roles : !contains(["roles/owner", "roles/editor"], r)
    ])
    error_message = "The owner and project-wide editor roles are not allowed. Grant specific roles instead."
  }

  validation {
    condition = alltrue([
      for r in var.roles :
      can(regex("^(roles/[A-Za-z0-9_.]+|projects/[a-z0-9-]+/roles/[A-Za-z0-9_.]+)$", r))
    ])
    error_message = "Each role must be written as roles/<name> or projects/<project>/roles/<name>."
  }
}

variable "impersonator_members" {
  description = "Map of static label to federation principal (principalSet://...) allowed to impersonate this identity. Keys are static so the plan never depends on unknown values."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.impersonator_members : can(regex("^[a-z][a-z0-9_]*$", k))])
    error_message = "impersonator_members keys must be lowercase labels such as ci_repository."
  }

  validation {
    condition = alltrue([
      for k, m in var.impersonator_members :
      can(regex("^(principalSet|principal)://iam\\.googleapis\\.com/", m))
    ])
    error_message = "impersonator_members values must be federation principals (principalSet:// or principal://); users, groups and public principals are not allowed."
  }
}

variable "require_attribute_restricted_impersonation" {
  description = "True for the release-candidate identity: impersonation is only allowed through a principalSet scoped to one attribute value (the release-candidate workflow)."
  type        = bool
  default     = false
}

variable "act_as_members" {
  description = "Map of static label to member allowed to attach this identity to a deployed service (act as). Granted on this identity only."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.act_as_members : can(regex("^[a-z][a-z0-9_]*$", k))])
    error_message = "act_as_members keys must be lowercase labels."
  }

  validation {
    condition     = alltrue([for k, m in var.act_as_members : !contains(["allUsers", "allAuthenticatedUsers"], m)])
    error_message = "Public principals are not allowed."
  }
}
