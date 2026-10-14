variable "project_id" {
  description = "Cloud project that owns the index. Supplied by the environment root."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid cloud project id."
  }
}

variable "environment" {
  description = "Environment name. One of dev, stage, prod-like. It is part of the bucket and data store ids."
  type        = string

  validation {
    condition     = contains(["dev", "stage", "prod-like"], var.environment)
    error_message = "environment must be one of dev, stage, prod-like."
  }
}

variable "location" {
  description = "Region of the corpus bucket. The data store itself is global."
  type        = string
  default     = "us-central1"

  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+$", var.location))
    error_message = "location must be a region such as us-central1."
  }
}

variable "chunk_size_tokens" {
  description = "Token limit of one retrieved passage. Agent Search accepts 100 to 500; shorter is more precise, longer keeps a rule with its exceptions."
  type        = number
  default     = 500

  validation {
    condition     = var.chunk_size_tokens >= 100 && var.chunk_size_tokens <= 500
    error_message = "chunk_size_tokens must be between 100 and 500."
  }
}

variable "search_members" {
  description = "IAM members that may query the index, for example user:you@example.com for local runs or the assistant's service account."
  type        = list(string)
  default     = []
}

variable "ingest_members" {
  description = "IAM members that may upload the corpus and import it into the data store."
  type        = list(string)
  default     = []
}
