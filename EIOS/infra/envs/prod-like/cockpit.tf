# Cockpit deployment: a public web UI that signs operators in, and a private API reached only
# through the web service's identity. Operator identity comes from Identity Platform ID tokens;
# action intents are signed with the KMS key and approval state lives in Firestore.

data "google_project" "this" {
  project_id = var.project_id
}

locals {
  # Cloud Run's deterministic URL form, so the two services can reference each other without a cycle.
  run_url_suffix  = "${data.google_project.this.number}.${var.region}.run.app"
  cockpit_web_url = "https://eios-web-${local.run_url_suffix}"

  cockpit_api_roles = concat(local.runtime_roles, ["roles/aiplatform.user"])

  cockpit_extra_apis = [
    "aiplatform.googleapis.com",
    "apikeys.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudtrace.googleapis.com",
    "telemetry.googleapis.com", # ADK exports spans to it over OTLP
    "identitytoolkit.googleapis.com",
  ]
}

resource "google_project_service" "cockpit" {
  for_each = toset(local.cockpit_extra_apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "identity_cockpit_api" {
  source = "../../modules/service_identity"

  project_id     = var.project_id
  environment    = local.environment
  service        = "eios_api"
  roles          = local.cockpit_api_roles
  act_as_members = { pipeline = module.identity_pipeline.member }

  depends_on = [module.project_baseline, google_project_service.cockpit]
}

# Screening templates for the assistant (spec 021 FR-015): what the operator asks and what the assistant answers. The
# API's own identity is the only caller granted `roles/modelarmor.user`. Sanitize logging stays off: it can carry
# operator text, and this environment is where real data would flow.
module "model_armor" {
  source = "../../modules/model_armor"

  project_id       = var.project_id
  environment      = local.environment
  location         = var.region
  sanitize_members = [module.identity_cockpit_api.member]
}

module "identity_cockpit_web" {
  source = "../../modules/service_identity"

  project_id     = var.project_id
  environment    = local.environment
  service        = "eios_web"
  roles          = local.runtime_roles
  act_as_members = { pipeline = module.identity_pipeline.member }

  depends_on = [module.project_baseline]
}

# The API is private: only the web service's identity may invoke it.
module "service_cockpit_api" {
  source = "../../modules/run_service"
  count  = var.cockpit_api_image == null ? 0 : 1

  project_id            = var.project_id
  environment           = local.environment
  region                = var.region
  service               = "eios_api"
  image                 = var.cockpit_api_image
  service_account_email = module.identity_cockpit_api.email
  stateful              = false
  warm_start_required   = false
  min_instances         = 1 # keep one warm: the engines are built at start-up, and an idle demo must not scale to zero
  max_instances         = 5
  cpu                   = "1"
  memory                = "2Gi" # 1Gi was exceeded (1,066 MiB used `[MEASURED]`) once the geo engines, graph tables and prepared briefs were deployed
  deletion_protection   = false # [ASSUMPTION] hackathon environment; tighten before real use
  invoker_members       = { cockpit_web = module.identity_cockpit_web.member }

  env_vars = merge(local.geo_env, {
    EIOS_ENVIRONMENT         = local.environment
    EIOS_AUTH_MODE           = "firebase"
    EIOS_FIREBASE_PROJECT_ID = var.project_id
    EIOS_CORS_ORIGINS        = local.cockpit_web_url
    EIOS_PERSISTENCE         = "firestore"
    EIOS_FIRESTORE_DATABASE  = module.state_stores.database_id
    EIOS_KMS_KEY_VERSION     = "${module.secret_store.signing_key_id}/cryptoKeyVersions/1"
    GOOGLE_CLOUD_PROJECT     = var.project_id
    GOOGLE_CLOUD_LOCATION    = "global"
    # ADK's turn, model and tool spans go to Cloud Trace; prompt and answer text is kept off them in code
    # (observability/cloud_trace.py). The runtime identity holds roles/cloudtrace.agent, the role Google's agent
    # scaffold grants for this exporter; the first deploy must confirm spans arrive (docs/cloud-trace.md).
    EIOS_TRACE_EXPORT = "cloud_trace"
    EIOS_SERVICE_NAME = "eios-api"
    # Vertex AI with the service identity instead of an API key. The assistant's models come from the registry in
    # the image (llm_gateway/providers/assistant_models.yaml), not from an environment variable.
    EIOS_WARM_BACKEND                  = var.warm_backend
    EIOS_WARM_PROJECT                  = var.project_id
    GOOGLE_GENAI_USE_ENTERPRISE        = "true"
    EIOS_MODEL_ARMOR_PROMPT_TEMPLATE   = module.model_armor.prompt_template_name
    EIOS_MODEL_ARMOR_RESPONSE_TEMPLATE = module.model_armor.response_template_name
  })

  secret_env = {
    EIOS_CASHIER_WEBHOOK_SECRET = { secret_id = "cashier_webhook_secret" }
    EIOS_HMAC_SALT              = { secret_id = "hmac_salt" }
  }

  depends_on = [module.artifact_registry, module.state_stores, module.secret_store]
}

# The web UI is the only public entry point; it enforces operator sign-in and proxies to the API.
module "service_cockpit_web" {
  source = "../../modules/run_service"
  count  = var.cockpit_web_image == null ? 0 : 1

  project_id              = var.project_id
  environment             = local.environment
  region                  = var.region
  service                 = "eios_web" # public entry point: https://eios-web-<project number>.<region>.run.app
  image                   = var.cockpit_web_image
  service_account_email   = module.identity_cockpit_web.email
  stateful                = false
  warm_start_required     = false
  min_instances           = 0
  max_instances           = 5
  deletion_protection     = false # [ASSUMPTION] hackathon environment; tighten before real use
  allow_public_invocation = true

  # The audience of the service-to-service ID token must be the API's own URL as Cloud Run reports it.
  env_vars = merge(
    {
      EIOS_BACKEND_URL          = module.service_cockpit_api[0].uri
      EIOS_BACKEND_IAM_AUDIENCE = module.service_cockpit_api[0].uri
    },
    # Reviewer access shown on the login page, set only where the owner chose to publish it (see variables.tf).
    var.demo_access == null ? {} : { EIOS_DEMO_ACCESS = var.demo_access },
  )

  depends_on = [module.artifact_registry, module.service_cockpit_api]
}

# Public client configuration for the browser (an API key restricted to the Identity Platform APIs).
resource "google_apikeys_key" "web_auth" {
  project = var.project_id
  # Key ids stay reserved after deletion, so rotating means a new id (r2, r3, ...). Rotated 2026-10-13 after
  # the previous key appeared in a committed plan file.
  name         = "eios-web-auth-r2"
  display_name = "eios-web-auth-r2"

  restrictions {
    api_targets {
      service = "identitytoolkit.googleapis.com"
    }
    api_targets {
      service = "securetoken.googleapis.com"
    }
    browser_key_restrictions {
      allowed_referrers = ["${local.cockpit_web_url}/*"]
    }
  }

  depends_on = [google_project_service.cockpit]
}

# Operators are provisioned by an administrator; there is no self-service sign-up.
resource "google_identity_platform_config" "auth" {
  project = var.project_id

  sign_in {
    email {
      enabled           = true
      password_required = true
    }
  }

  client {
    permissions {
      disabled_user_signup   = true
      disabled_user_deletion = true
    }
  }

  authorized_domains = ["${replace(local.cockpit_web_url, "https://", "")}", "${var.project_id}.firebaseapp.com"]

  depends_on = [google_project_service.cockpit]
}

output "cockpit_web_url" {
  description = "Public URL of the cockpit."
  value       = local.cockpit_web_url
}

output "cockpit_web_api_key" {
  description = "Browser API key for Identity Platform sign-in (public client configuration)."
  value       = google_apikeys_key.web_auth.key_string
  sensitive   = true
}
