# Model Armor screening templates for the ADK assistant (ADR-019, spec 021 FR-015): one for what the operator
# types, one for what the model writes. The assistant addresses them by full resource name and fails closed if
# screening is unavailable (src/eios/assistant/safety.py). Templates are regional, never global.

terraform {
  # [SPIKE] The minimum Terraform version and the provider version are not pinned as facts.
  required_version = ">= 1.6"

  required_providers {
    google = {
      source = "hashicorp/google"
      # version = "REPLACE_ME_after_spike" # [SPIKE] unverified until the first reviewed init
    }
  }
}

locals {
  rai_filter_types = ["HATE_SPEECH", "HARASSMENT", "SEXUALLY_EXPLICIT", "DANGEROUS"]
  prompt_id        = "eios-prompt-${var.environment}"
  response_id      = "eios-response-${var.environment}"
}

resource "google_project_service" "model_armor" {
  project            = var.project_id
  service            = "modelarmor.googleapis.com"
  disable_on_destroy = false
}

# What the operator types: Responsible-AI categories, prompt injection and jailbreak, malicious links.
# Sensitive Data Protection is deliberately absent: answers carry account ids, partner names and amounts, and a
# data-loss filter would block legitimate ones. Turn it on only after reading real traffic.
resource "google_model_armor_template" "prompt" {
  project     = var.project_id
  location    = var.location
  template_id = local.prompt_id

  labels = {
    environment = var.environment
    purpose     = "assistant-input-screening"
  }

  filter_config {
    rai_settings {
      dynamic "rai_filters" {
        for_each = local.rai_filter_types
        content {
          filter_type      = rai_filters.value
          confidence_level = var.rai_confidence
        }
      }
    }
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = var.prompt_injection_confidence
    }
    malicious_uri_filter_settings {
      filter_enforcement = "ENABLED"
    }
  }

  template_metadata {
    enforcement_type        = var.enforcement_type
    log_sanitize_operations = var.log_sanitize_operations
  }

  depends_on = [google_project_service.model_armor]
}

# What the model writes: Responsible-AI categories and malicious links. Prompt injection is an input concern.
resource "google_model_armor_template" "response" {
  project     = var.project_id
  location    = var.location
  template_id = local.response_id

  labels = {
    environment = var.environment
    purpose     = "assistant-output-screening"
  }

  filter_config {
    rai_settings {
      dynamic "rai_filters" {
        for_each = local.rai_filter_types
        content {
          filter_type      = rai_filters.value
          confidence_level = var.rai_confidence
        }
      }
    }
    malicious_uri_filter_settings {
      filter_enforcement = "ENABLED"
    }
  }

  template_metadata {
    enforcement_type        = var.enforcement_type
    log_sanitize_operations = var.log_sanitize_operations
  }

  depends_on = [google_project_service.model_armor]
}

# The identities that may call the screening API (the service identity of eios-api, or a developer locally).
resource "google_project_iam_member" "sanitize" {
  for_each = toset(var.sanitize_members)

  project = var.project_id
  role    = "roles/modelarmor.user"
  member  = each.value
}
