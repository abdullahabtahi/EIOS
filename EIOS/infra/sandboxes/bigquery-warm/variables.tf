variable "project_id" {
  description = "The dev sandbox project. Pass it with -var, not a committed tfvars file."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid cloud project id."
  }
}

variable "region" {
  description = "Region of the datasets."
  type        = string
  default     = "us-central1"
}

variable "reader_members" {
  description = "IAM members that may query, for example user:you@example.com for local runs."
  type        = list(string)
  default     = []
}

variable "writer_members" {
  description = "IAM members that may load batches, for example user:you@example.com."
  type        = list(string)
  default     = []
}
