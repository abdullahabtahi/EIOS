variable "geo_graph_backend" {
  description = "Where graph queries run: local (the double over the same tables, no cloud cost) or bigquery (BigQuery Graph on an Enterprise reservation; load warm_graph first)."
  type        = string
  default     = "local"

  validation {
    condition     = contains(["local", "bigquery"], var.geo_graph_backend)
    error_message = "geo_graph_backend must be local or bigquery."
  }
}

variable "graph_max_slots" {
  description = "The most slots the graph reservation may autoscale to (BigQuery needs a multiple of 50). The baseline is 0, so this bounds the worst case."
  type        = number
  default     = 50 # the smallest allowed; the largest graph job measured used 191 slot-milliseconds [MEASURED]

  validation {
    condition     = var.graph_max_slots > 0 && var.graph_max_slots % 50 == 0
    error_message = "graph_max_slots must be a positive multiple of 50."
  }
}

variable "ambient_top_n" {
  description = "How many top alerts get a prepared brief when an API instance starts (0 = none). A fresh brief is not rebuilt."
  type        = number
  default     = 0
}

variable "knowledge_data_store" {
  description = "Agent Search data store id for regulation text; empty means none is configured and the tool says so."
  type        = string
  default     = ""
}

variable "knowledge_project_id" {
  description = "The project that holds the Agent Search data store. Supply from a tfvars file that is not committed."
  type        = string
  default     = ""
}
