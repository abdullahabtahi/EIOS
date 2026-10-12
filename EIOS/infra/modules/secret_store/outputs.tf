output "secret_ids" {
  description = "Ids of the secret containers created. No values are exposed."
  value       = sort(keys(google_secret_manager_secret.this))
}

output "signing_key_enabled" {
  description = "Whether the signing key ring and key exist in this environment."
  value       = var.signing_key_enabled
}

output "key_ring_id" {
  description = "Key ring id, or null when signing_key_enabled is false."
  value       = one(google_kms_key_ring.signing[*].id)
}

output "signing_key_id" {
  description = "Asymmetric signing key id, or null when signing_key_enabled is false."
  value       = one(google_kms_crypto_key.signing[*].id)
}

output "signing_key_algorithm" {
  description = "Signing algorithm, or null when signing_key_enabled is false."
  value       = var.signing_key_enabled ? "EC_SIGN_P256_SHA256" : null
}
