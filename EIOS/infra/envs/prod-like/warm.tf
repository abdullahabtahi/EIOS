# The warm tier (docs/warm-tier.md): BigQuery datasets and tables for history, generated from the contracts. The API
# identity reads them; whoever runs `python -m eios.warm load` writes (listed in `warm_writer_members`, never committed).
# The service keeps using the local double until `warm_backend` is set to "bigquery", which is done after the history
# has been loaded: pointing at empty tables would answer "no activity" for accounts that have plenty.

module "bigquery_warm" {
  source = "../../modules/bigquery_warm"

  project_id     = var.project_id
  environment    = local.environment
  location       = var.region
  reader_members = [module.identity_cockpit_api.member]
  writer_members = var.warm_writer_members
}
