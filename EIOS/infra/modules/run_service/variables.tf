variable "project_id" {
  description = "Cloud project that owns the service. Supplied by the environment root."
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

variable "region" {
  description = "Region the service runs in."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]+$", var.region))
    error_message = "region must be a lowercase region name."
  }
}

variable "service" {
  description = "Service name as in infra/identities.yaml (for example skeleton_core)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]{3,28}$", var.service))
    error_message = "service must be lowercase letters, digits and underscores, starting with a letter."
  }
}

variable "image" {
  description = "Container image reference by digest: <registry path>/<image>@sha256:<64 hex>. Tags are rejected."
  type        = string

  validation {
    condition     = can(regex("@sha256:[a-f0-9]{64}$", var.image))
    error_message = "image must be referenced by digest (…@sha256:<64 hex characters>), not by tag."
  }
}

variable "service_account_email" {
  description = "Email of the service's own identity (from the service_identity module). The default compute identity is rejected."
  type        = string

  validation {
    condition     = !can(regex("-compute@developer\\.gserviceaccount\\.com$", var.service_account_email))
    error_message = "The default compute service account is not allowed; each service uses its own identity."
  }
}

variable "min_instances" {
  description = "Minimum running instances. Must be set explicitly by the caller. prod-like sets at least 1 for stateful services to avoid cold starts."
  type        = number

  validation {
    condition     = var.min_instances >= 0 && floor(var.min_instances) == var.min_instances
    error_message = "min_instances must be a whole number, zero or more."
  }
}

variable "max_instances" {
  description = "Maximum running instances. The default is an [ASSUMPTION] cost guard for skeleton services."
  type        = number
  default     = 2

  validation {
    condition     = var.max_instances >= 1 && floor(var.max_instances) == var.max_instances
    error_message = "max_instances must be a whole number of at least 1."
  }
}

variable "stateful" {
  description = "Whether the service holds or depends on state that is expensive to rebuild (warm-start applies)."
  type        = bool
  default     = false
}

variable "warm_start_required" {
  description = "True in prod-like: a stateful service must then keep min_instances at 1 or more."
  type        = bool
  default     = false
}

variable "cpu" {
  description = "CPU limit per instance. Default is an [ASSUMPTION] sized for skeleton services."
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory limit per instance. Default is an [ASSUMPTION] sized for skeleton services."
  type        = string
  default     = "512Mi"
}

variable "ingress" {
  description = "Ingress setting. All traffic is allowed at the network layer, but invocation still needs an explicit invoker grant (public principals are rejected)."
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"

  validation {
    condition     = contains(["INGRESS_TRAFFIC_ALL", "INGRESS_TRAFFIC_INTERNAL_ONLY", "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"], var.ingress)
    error_message = "ingress must be a valid Cloud Run ingress setting."
  }
}

variable "deletion_protection" {
  description = "Block deletion of the service by Terraform. True by default; dev may disable it to allow teardown."
  type        = bool
  default     = true
}

variable "env_vars" {
  description = "Plain environment variables. Secret-looking names are rejected; use secret_env for secrets."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, v in var.env_vars : !can(regex("(?i)(secret|password|token|credential|api_?key|private_?key)", k))])
    error_message = "A variable name looks like a secret. Use secret_env so the value is read from the managed secret store."
  }
}

variable "secret_env" {
  description = "Environment variables sourced from the managed secret store: name to secret id and version."
  type = map(object({
    secret_id = string
    version   = optional(string, "latest")
  }))
  default = {}
}

variable "invoker_members" {
  description = "Map of static label to member allowed to invoke the service. Public principals are rejected."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, m in var.invoker_members : !contains(["allUsers", "allAuthenticatedUsers"], m)])
    error_message = "Public invocation is not allowed. Grant specific identities."
  }
}

variable "allow_public_invocation" {
  description = "Grant roles/run.invoker to allUsers. Only for the one public entry point (the web UI), which enforces operator sign-in itself. Every other service stays private; this is a deliberate, reviewed exception."
  type        = bool
  default     = false
}
