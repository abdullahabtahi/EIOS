variable "project_id" {
  description = "Cloud project for this environment. Supplied through a tfvars file that is not committed."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid cloud project id."
  }
}

variable "region" {
  description = "Region for regional resources (Cloud Run, Firestore, buckets, registry, key ring)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]+$", var.region))
    error_message = "region must be a lowercase region name."
  }
}

variable "workload_identity_pool_name" {
  description = "Full name of the CI workload identity pool, from the bootstrap output workload_identity_pool_name."
  type        = string

  validation {
    condition     = can(regex("^projects/[0-9]+/locations/global/workloadIdentityPools/[a-z0-9-]+$", var.workload_identity_pool_name))
    error_message = "workload_identity_pool_name must look like projects/<number>/locations/global/workloadIdentityPools/<pool>."
  }
}

variable "ci_repository" {
  description = "Repository allowed to authenticate through federation, as owner/name."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.ci_repository))
    error_message = "ci_repository must be written as owner/name."
  }
}

variable "release_candidate_git_ref" {
  description = "Git ref the release-candidate workflow must run from. The default is an [ASSUMPTION]."
  type        = string
  default     = "refs/heads/main"

  validation {
    condition     = can(regex("^refs/(heads|tags)/.+$", var.release_candidate_git_ref))
    error_message = "release_candidate_git_ref must be a full ref such as refs/heads/main."
  }
}

variable "enforce_guardrails" {
  description = "Enforce the project-level guardrail policies."
  type        = bool
  default     = true
}

variable "evidence_retention_days" {
  description = "Evidence retention in days. stage value is an [ASSUMPTION]."
  type        = number
  default     = 30

  validation {
    condition     = var.evidence_retention_days >= 1 && floor(var.evidence_retention_days) == var.evidence_retention_days
    error_message = "evidence_retention_days must be a whole number of at least 1."
  }
}

variable "evidence_lock_retention" {
  description = "Lock the evidence retention policy. false in stage so the project can be torn down."
  type        = bool
  default     = false
}

variable "skeleton_core_image" {
  description = "skeleton_core image by digest. null until the first image is pushed; no service is created while null."
  type        = string
  default     = null

  validation {
    condition     = var.skeleton_core_image == null || can(regex("@sha256:[a-f0-9]{64}$", var.skeleton_core_image))
    error_message = "skeleton_core_image must be referenced by digest (…@sha256:<64 hex characters>)."
  }
}

variable "skeleton_edge_image" {
  description = "skeleton_edge image by digest. null until the first image is pushed; no service is created while null."
  type        = string
  default     = null

  validation {
    condition     = var.skeleton_edge_image == null || can(regex("@sha256:[a-f0-9]{64}$", var.skeleton_edge_image))
    error_message = "skeleton_edge_image must be referenced by digest (…@sha256:<64 hex characters>)."
  }
}

variable "billing_account" {
  description = "Billing account ID."
  type        = string
}

variable "notification_email" {
  description = "Email address for budget alerts."
  type        = string
}
