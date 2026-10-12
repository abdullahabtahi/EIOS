variable "project_id" {
  description = "Cloud project that owns the database. Supplied by the environment root."
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

variable "location_id" {
  description = "Firestore location id."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]+$", var.location_id))
    error_message = "location_id must be a lowercase location name."
  }
}

variable "database_id" {
  description = "Named database id, so the gateway client addresses it explicitly."
  type        = string
  default     = "eios-state"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,61}[a-z0-9]$", var.database_id))
    error_message = "database_id must be lowercase letters, digits and hyphens, 4 to 63 characters."
  }
}

variable "counter_collection" {
  description = "Collection holding gateway daily token counters."
  type        = string
  default     = "gateway_counters"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]{2,62}$", var.counter_collection))
    error_message = "counter_collection must be lowercase letters, digits and underscores."
  }
}

variable "replay_collection" {
  description = "Collection holding the gateway replay cache (entries expire through TTL on expires_at)."
  type        = string
  default     = "gateway_replay_cache"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]{2,62}$", var.replay_collection))
    error_message = "replay_collection must be lowercase letters, digits and underscores."
  }
}

variable "deletion_protection" {
  description = "Protect the database from deletion. True by default; dev may disable it to allow teardown."
  type        = bool
  default     = true
}

variable "user_members" {
  description = "Map of static label to service account member that may read and write this database."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.user_members : can(regex("^serviceAccount:", m))])
    error_message = "Only service account members may use the state database."
  }
}
