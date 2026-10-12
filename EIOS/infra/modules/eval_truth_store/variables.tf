variable "project_id" {
  description = "Cloud project that owns the buckets. Supplied by the environment root."
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

variable "location" {
  description = "Bucket location."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9-]+$", var.location))
    error_message = "location must be a bucket location name."
  }
}

variable "bucket_name_suffix" {
  description = "Suffix appended to the project id to make a globally unique bucket name."
  type        = string
  default     = "eval-truth"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.bucket_name_suffix))
    error_message = "bucket_name_suffix must be lowercase letters, digits and hyphens."
  }
}

variable "reader_members" {
  description = "Map of static label to service account member that may read the development and validation splits. Only identities with can_read_eval_truth true in infra/identities.yaml (harness, pipeline) belong here."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for k, m in var.reader_members : can(regex("^serviceAccount:", m))
    ])
    error_message = "Only service account members may read ground truth; users, groups and public principals are not allowed."
  }
}

variable "sealed_reader_members" {
  description = "Map of static label to service account member that may read the sealed split. Only the release-candidate identity belongs here."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for k, m in var.sealed_reader_members : can(regex("^serviceAccount:", m))
    ])
    error_message = "Only service account members may read the sealed split."
  }

  validation {
    condition     = length(var.sealed_reader_members) <= 1
    error_message = "The sealed split is readable by one identity only: the release-candidate identity."
  }
}
