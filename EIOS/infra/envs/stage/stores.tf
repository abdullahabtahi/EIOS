module "secret_store" {
  source = "../../modules/secret_store"

  project_id          = var.project_id
  environment         = local.environment
  signing_key_enabled = false # stage has no signing key; see docs/environments.md
  kms_location        = var.region

  secrets = {
    llm_provider_credential = {
      accessors = { skeleton_core = module.identity_skeleton_core.member }
    }
  }

  depends_on = [module.project_baseline]
}

module "eval_truth_store" {
  source = "../../modules/eval_truth_store"

  project_id  = var.project_id
  environment = local.environment
  location    = var.region

  reader_members = {
    pipeline     = module.identity_pipeline.member
    eval_harness = module.identity_eval_harness.member
  }
  sealed_reader_members = {
    release_candidate = module.identity_release_candidate.member
  }

  depends_on = [module.project_baseline]
}

module "evidence_store" {
  source = "../../modules/evidence_store"

  project_id     = var.project_id
  environment    = local.environment
  location       = var.region
  retention_days = var.evidence_retention_days
  lock_retention = var.evidence_lock_retention

  writer_members = {
    pipeline          = module.identity_pipeline.member
    eval_harness      = module.identity_eval_harness.member
    release_candidate = module.identity_release_candidate.member
  }
  reader_members = {
    pipeline = module.identity_pipeline.member
  }

  depends_on = [module.project_baseline]
}

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id  = var.project_id
  environment = local.environment
  location    = var.region

  writer_members = { pipeline = module.identity_pipeline.member }

  depends_on = [module.project_baseline]
}

module "state_stores" {
  source = "../../modules/state_stores"

  project_id          = var.project_id
  environment         = local.environment
  location_id         = var.region
  deletion_protection = false # [ASSUMPTION] stage may be torn down

  user_members = {
    skeleton_edge = module.identity_skeleton_edge.member
    skeleton_core = module.identity_skeleton_core.member
  }

  depends_on = [module.project_baseline]
}

# Services are created once their images exist. Images are referenced by digest only;
# until a digest is supplied the identities and stores above exist without a service.
module "service_skeleton_core" {
  source = "../../modules/run_service"
  count  = var.skeleton_core_image == null ? 0 : 1

  project_id            = var.project_id
  environment           = local.environment
  region                = var.region
  service               = "skeleton_core"
  image                 = var.skeleton_core_image
  service_account_email = module.identity_skeleton_core.email
  stateful              = true
  warm_start_required   = false
  min_instances         = 0 # [ASSUMPTION] scale to zero in stage
  deletion_protection   = false
  env_vars              = { EIOS_ENVIRONMENT = local.environment }
  invoker_members       = { skeleton_edge = module.identity_skeleton_edge.member }

  depends_on = [module.artifact_registry, module.state_stores]
}

module "service_skeleton_edge" {
  source = "../../modules/run_service"
  count  = var.skeleton_edge_image == null ? 0 : 1

  project_id            = var.project_id
  environment           = local.environment
  region                = var.region
  service               = "skeleton_edge"
  image                 = var.skeleton_edge_image
  service_account_email = module.identity_skeleton_edge.email
  stateful              = true
  warm_start_required   = false
  min_instances         = 0 # [ASSUMPTION] scale to zero in stage
  deletion_protection   = false

  env_vars = {
    EIOS_ENVIRONMENT = local.environment
    EIOS_CORE_URL    = try(module.service_skeleton_core[0].uri, "")
  }

  depends_on = [module.artifact_registry, module.state_stores]
}
