output "bucket_name" {
  description = "Bucket holding the development and validation ground-truth splits."
  value       = google_storage_bucket.truth.name
}

output "sealed_bucket_name" {
  description = "Bucket holding the sealed ground-truth split."
  value       = google_storage_bucket.sealed.name
}

output "reader_labels" {
  description = "Static labels of the identities granted read on the development and validation splits."
  value       = sort(keys(var.reader_members))
}

output "sealed_reader_labels" {
  description = "Static labels of the identities granted read on the sealed split."
  value       = sort(keys(var.sealed_reader_members))
}
