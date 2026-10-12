# Built-in resource only: validates without downloading any provider.
resource "terraform_data" "marker" {
  input = "clean-skeleton"
}

output "marker" {
  value = terraform_data.marker.output
}
