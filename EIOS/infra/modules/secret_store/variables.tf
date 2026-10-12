variable "project_id" {
  description = "Cloud project that owns the secrets and the key ring. Supplied by the environment root."
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

variable "secrets" {
  description = "Map of secret id to its accessors. accessors maps a static label to an IAM member that may read the secret. Only containers are created; values are never in Terraform."
  type = map(object({
    accessors = optional(map(string), {})
  }))
  default = {}

  validation {
    condition     = alltrue([for id, s in var.secrets : can(regex("^[A-Za-z][A-Za-z0-9_-]{0,254}$", id))])
    error_message = "Secret ids must start with a letter and use letters, digits, hyphens and underscores."
  }

  validation {
    condition = alltrue(flatten([
      for id, s in var.secrets : [
        for label, member in s.accessors : !contains(["allUsers", "allAuthenticatedUsers"], member)
      ]
    ]))
    error_message = "Public principals cannot read secrets."
  }
}

variable "signing_key_enabled" {
  description = "Create the key ring and the asymmetric ECDSA P-256 signing key. True in prod-like, false elsewhere."
  type        = bool
  default     = false
}

variable "kms_location" {
  description = "Location of the key ring. Required when signing_key_enabled is true."
  type        = string
  default     = null

  validation {
    condition     = var.kms_location == null || can(regex("^[a-z][a-z0-9-]+$", var.kms_location))
    error_message = "kms_location must be a lowercase location name."
  }
}

variable "key_ring_name" {
  description = "Name of the key ring (cannot be deleted once created)."
  type        = string
  default     = "eios-signing"

  validation {
    condition     = can(regex("^[A-Za-z0-9_-]{1,63}$", var.key_ring_name))
    error_message = "key_ring_name may use letters, digits, hyphens and underscores."
  }
}

variable "signing_key_name" {
  description = "Name of the asymmetric signing key."
  type        = string
  default     = "action-intent-signing"

  validation {
    condition     = can(regex("^[A-Za-z0-9_-]{1,63}$", var.signing_key_name))
    error_message = "signing_key_name may use letters, digits, hyphens and underscores."
  }
}

variable "signing_key_protection_level" {
  description = "SOFTWARE or HSM. The default is an [ASSUMPTION]; the choice is reviewed with the first cost reconciliation."
  type        = string
  default     = "SOFTWARE"

  validation {
    condition     = contains(["SOFTWARE", "HSM"], var.signing_key_protection_level)
    error_message = "signing_key_protection_level must be SOFTWARE or HSM."
  }
}

variable "signer_members" {
  description = "Map of static label to member allowed to sign with the key. Empty until the approval service exists."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.signer_members : !contains(["allUsers", "allAuthenticatedUsers"], m)])
    error_message = "Public principals cannot sign."
  }
}

variable "verifier_members" {
  description = "Map of static label to member allowed to read the public key for verification."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.verifier_members : !contains(["allUsers", "allAuthenticatedUsers"], m)])
    error_message = "Public principals are not allowed."
  }
}
