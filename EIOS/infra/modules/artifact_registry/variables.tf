variable "project_id" {
  description = "Cloud project that owns the repository. Supplied by the environment root."
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
  description = "Repository location (a region)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]+$", var.location))
    error_message = "location must be a lowercase location name."
  }
}

variable "repository_id" {
  description = "Repository id."
  type        = string
  default     = "images"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,62}$", var.repository_id))
    error_message = "repository_id must be lowercase letters, digits and hyphens."
  }
}

variable "writer_members" {
  description = "Map of static label to member that may push images (the pipeline identity)."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.writer_members : can(regex("^serviceAccount:", m))])
    error_message = "Only service account members may push images."
  }
}

variable "reader_members" {
  description = "Map of static label to member that may pull images."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.reader_members : can(regex("^serviceAccount:", m))])
    error_message = "Only service account members may pull images."
  }
}
