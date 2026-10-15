# Warm tier tables (docs/warm-tier.md): one dataset per bounded context, one table per data product, partitioned by day
# and clustered, with the schema generated from the contracts (tables.json, written by tools/gen_warm_tables.py and
# checked by a test, so the layout cannot drift from what ingestion validates). Queries must name a partition.

terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }
}

locals {
  tables   = jsondecode(file("${path.module}/tables.json"))
  datasets = toset([for t in local.tables : t.dataset])
  by_key   = { for t in local.tables : "${t.dataset}.${t.table}" => t }
  # Granting a dataset to a member needs the pair, so build the cross product once.
  reader_grants = { for pair in setproduct(local.datasets, var.reader_members) : "${pair[0]}|${pair[1]}" => { dataset = pair[0], member = pair[1] } }
  writer_grants = { for pair in setproduct(local.datasets, var.writer_members) : "${pair[0]}|${pair[1]}" => { dataset = pair[0], member = pair[1] } }
  labels = {
    environment = var.environment
    purpose     = "warm-tier"
  }
}

resource "google_project_service" "bigquery" {
  project            = var.project_id
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_bigquery_dataset" "this" {
  for_each = local.datasets

  project                    = var.project_id
  dataset_id                 = each.value
  location                   = var.location
  delete_contents_on_destroy = var.delete_contents_on_destroy
  labels                     = local.labels

  depends_on = [google_project_service.bigquery]
}

resource "google_bigquery_table" "this" {
  for_each = local.by_key

  project             = var.project_id
  dataset_id          = google_bigquery_dataset.this[each.value.dataset].dataset_id
  table_id            = each.value.table
  schema              = jsonencode(each.value.schema)
  deletion_protection = var.deletion_protection
  labels              = local.labels

  # A query that does not name a partition is refused by BigQuery itself: the cost guard does not depend on our code.
  require_partition_filter = true

  time_partitioning {
    type  = "DAY"
    field = each.value.partition_field
  }

  clustering = length(each.value.cluster_fields) == 0 ? null : each.value.cluster_fields
}

# Who may run queries (project level) and read or load the datasets.
resource "google_project_iam_member" "job_user" {
  for_each = toset(concat(var.reader_members, var.writer_members))

  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = each.value
}

resource "google_bigquery_dataset_iam_member" "reader" {
  for_each = local.reader_grants

  project    = var.project_id
  dataset_id = google_bigquery_dataset.this[each.value.dataset].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = each.value.member
}

resource "google_bigquery_dataset_iam_member" "writer" {
  for_each = local.writer_grants

  project    = var.project_id
  dataset_id = google_bigquery_dataset.this[each.value.dataset].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = each.value.member
}
