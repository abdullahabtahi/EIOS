variable "project_id" {
  description = "Cloud project that owns the templates. Supplied by the environment root."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid cloud project id."
  }
}

variable "environment" {
  description = "Environment name. One of dev, stage, prod-like. It is part of the template ids."
  type        = string

  validation {
    condition     = contains(["dev", "stage", "prod-like"], var.environment)
    error_message = "environment must be one of dev, stage, prod-like."
  }
}

variable "location" {
  description = "Region of the templates. Model Armor is regional; keep it near the service that calls it. Not global."
  type        = string
  default     = "us-central1"

  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+$", var.location))
    error_message = "location must be a region such as us-central1, not global."
  }
}

variable "rai_confidence" {
  description = "Confidence at which a Responsible-AI category blocks. LOW_AND_ABOVE blocks the most, HIGH the least."
  type        = string
  default     = "MEDIUM_AND_ABOVE"

  validation {
    condition     = contains(["LOW_AND_ABOVE", "MEDIUM_AND_ABOVE", "HIGH"], var.rai_confidence)
    error_message = "rai_confidence must be LOW_AND_ABOVE, MEDIUM_AND_ABOVE or HIGH."
  }
}

variable "prompt_injection_confidence" {
  description = "Confidence at which prompt injection or a jailbreak attempt blocks."
  type        = string
  default     = "MEDIUM_AND_ABOVE"

  validation {
    condition     = contains(["LOW_AND_ABOVE", "MEDIUM_AND_ABOVE", "HIGH"], var.prompt_injection_confidence)
    error_message = "prompt_injection_confidence must be LOW_AND_ABOVE, MEDIUM_AND_ABOVE or HIGH."
  }
}

variable "enforcement_type" {
  description = "INSPECT_AND_BLOCK blocks on a match; INSPECT_ONLY records a match and lets it through (for tuning)."
  type        = string
  default     = "INSPECT_AND_BLOCK"

  validation {
    condition     = contains(["INSPECT_AND_BLOCK", "INSPECT_ONLY"], var.enforcement_type)
    error_message = "enforcement_type must be INSPECT_AND_BLOCK or INSPECT_ONLY."
  }
}

variable "log_sanitize_operations" {
  description = "Log each screening call, to tune thresholds. The log can carry operator text, so keep it off where real data flows."
  type        = bool
  default     = false
}

variable "sanitize_members" {
  description = "IAM members granted roles/modelarmor.user on the project, for example the eios-api service account."
  type        = list(string)
  default     = []
}
