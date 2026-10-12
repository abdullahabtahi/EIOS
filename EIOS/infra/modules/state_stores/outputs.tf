output "database_id" {
  description = "Firestore database id the gateway client must address."
  value       = google_firestore_database.state.name
}

output "counter_collection" {
  description = "Collection for gateway token counters."
  value       = var.counter_collection
}

output "replay_collection" {
  description = "Collection for the gateway replay cache."
  value       = var.replay_collection
}
