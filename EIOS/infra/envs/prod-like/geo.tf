# The geo feature (docs/geo-deploy-plan.md): the reference layer and graph datasets, the Enterprise reservation BigQuery
# Graph queries run on, and the Agent Search read for regulation text. Nothing here is applied by merging; it needs a plan
# shown to the owner first. Loading data into the datasets is a separate step (python -m eios.reference / eios.netintel /
# eios.graph).

locals {
  graph_on = var.geo_graph_backend == "bigquery"

  # The datasets the API reads. warm_graph exists only when the graph backend is BigQuery.
  geo_datasets = toset(concat(["warm_reference"], local.graph_on ? ["warm_graph"] : []))

  geo_labels = {
    app         = "eios"
    component   = "geo"
    environment = local.environment
  }

  # What the API container is told. Empty values are left out, so the defaults keep today's behaviour.
  geo_env = merge(
    local.graph_on ? {
      EIOS_GRAPH_BACKEND     = "bigquery"
      EIOS_GRAPH_PROJECT     = var.project_id
      EIOS_GRAPH_RESERVATION = google_bigquery_reservation.graph[0].id # the full path a job names
    } : {},
    var.ambient_top_n > 0 ? { EIOS_AMBIENT_TOP_N = tostring(var.ambient_top_n) } : {},
    var.knowledge_data_store != "" ? {
      EIOS_KNOWLEDGE_DATA_STORE = var.knowledge_data_store
      EIOS_KNOWLEDGE_PROJECT    = var.knowledge_project_id
    } : {},
  )
}

resource "google_bigquery_dataset" "geo" {
  for_each = local.geo_datasets

  project                    = var.project_id
  dataset_id                 = each.key
  location                   = var.region
  labels                     = local.geo_labels
  delete_contents_on_destroy = false
}

resource "google_bigquery_dataset_iam_member" "geo_reader" {
  for_each = local.geo_datasets

  project    = var.project_id
  dataset_id = google_bigquery_dataset.geo[each.key].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = module.identity_cockpit_api.member
}

resource "google_bigquery_dataset_iam_member" "geo_writer" {
  for_each = {
    for pair in setproduct(local.geo_datasets, var.warm_writer_members) : "${pair[0]}/${pair[1]}" => pair
  }

  project    = var.project_id
  dataset_id = google_bigquery_dataset.geo[each.value[0]].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = each.value[1]
}

# BigQuery runs GQL only on an Enterprise reservation. Baseline 0 means an idle reservation costs nothing; the cap bounds
# the worst case. Jobs name the reservation themselves, so nothing else in the project changes how it is billed.
resource "google_bigquery_reservation" "graph" {
  count = local.graph_on ? 1 : 0

  project       = var.project_id
  name          = "eios-graph"
  location      = var.region
  edition       = "ENTERPRISE"
  slot_capacity = 0

  autoscale {
    max_slots = var.graph_max_slots
  }
}

# Least privilege: the permission to name a reservation on a job, and nothing that manages reservations.
resource "google_project_iam_custom_role" "graph_reservation_user" {
  count = local.graph_on ? 1 : 0

  project     = var.project_id
  role_id     = "eiosGraphReservationUser"
  title       = "EIOS graph reservation user"
  description = "Run a query job on a named BigQuery reservation."
  permissions = ["bigquery.reservations.use"]
}

resource "google_project_iam_member" "graph_reservation_use" {
  count = local.graph_on ? 1 : 0

  project = var.project_id
  role    = google_project_iam_custom_role.graph_reservation_user[0].id
  member  = module.identity_cockpit_api.member
}

# Regulation text: the Agent Search data store may live in another project (the dev one). The API identity reads it.
resource "google_project_iam_member" "knowledge_viewer" {
  count = var.knowledge_project_id != "" ? 1 : 0

  project = var.knowledge_project_id
  role    = "roles/discoveryengine.viewer"
  member  = module.identity_cockpit_api.member
}
