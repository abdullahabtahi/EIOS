variable "project_id" {
  description = "Cloud project that owns the bucket. Supplied by the environment root."
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
  default     = "evidence"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$", var.bucket_name_suffix))
    error_message = "bucket_name_suffix must be lowercase letters, digits and hyphens."
  }
}

variable "retention_days" {
  description = "Retention period for evidence objects in days. The value per environment is an [ASSUMPTION] set in the environment root."
  type        = number

  validation {
    condition     = var.retention_days >= 1 && floor(var.retention_days) == var.retention_days
    error_message = "retention_days must be a whole number of at least 1."
  }
}

variable "lock_retention" {
  description = "Lock the retention policy. Irreversible once applied; true in prod-like, an explicit choice elsewhere (documented in docs/environments.md)."
  type        = bool
  default     = true
}

variable "writer_members" {
  description = "Map of static label to member that may create evidence objects (create only, no read, no overwrite)."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.writer_members : can(regex("^serviceAccount:", m))])
    error_message = "Only service account members may write evidence."
  }
}

variable "reader_members" {
  description = "Map of static label to member that may read evidence objects."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.reader_members : can(regex("^serviceAccount:", m))])
    error_message = "Only service account members may read evidence."
  }
}
