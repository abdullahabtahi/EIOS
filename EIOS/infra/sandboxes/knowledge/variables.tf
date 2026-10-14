variable "project_id" {
  description = "The dev sandbox project. Supplied through a tfvars file that is not committed."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid cloud project id."
  }
}

variable "region" {
  description = "Region of the corpus bucket."
  type        = string
  default     = "us-central1"
}

variable "search_members" {
  description = "IAM members that may query the index, for example user:you@example.com for local runs."
  type        = list(string)
  default     = []
}

variable "ingest_members" {
  description = "IAM members that may upload the corpus and import it, for example user:you@example.com."
  type        = list(string)
  default     = []
}
