variable "project_id" {
  description = "The dev sandbox project. Supplied through a tfvars file that is not committed."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid cloud project id."
  }
}

variable "region" {
  description = "Region of the templates."
  type        = string
  default     = "us-central1"
}

variable "sanitize_members" {
  description = "IAM members that may call the screening API, for example user:you@example.com for local runs."
  type        = list(string)
  default     = []
}
