variable "project_id" {
  description = "Cloud project that owns the datasets. Supplied by the environment root."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid cloud project id."
  }
}

variable "environment" {
  description = "Environment name. One of dev, stage, prod-like. It is a label on every dataset and table."
  type        = string

  validation {
    condition     = contains(["dev", "stage", "prod-like"], var.environment)
    error_message = "environment must be one of dev, stage, prod-like."
  }
}

variable "location" {
  description = "Dataset location. Keep it with the service that queries it; it cannot be changed after creation."
  type        = string
  default     = "us-central1"
}

variable "reader_members" {
  description = "IAM members that may query the warm tier, for example the eios-api service account."
  type        = list(string)
  default     = []
}

variable "writer_members" {
  description = "IAM members that may load batches, for example the operator running the loader."
  type        = list(string)
  default     = []
}

variable "deletion_protection" {
  description = "Refuse to destroy tables. [ASSUMPTION] off for the hackathon environments; turn on before real data."
  type        = bool
  default     = false
}

variable "delete_contents_on_destroy" {
  description = "Let a dataset be destroyed with its tables. [ASSUMPTION] on for the hackathon environments."
  type        = bool
  default     = true
}
