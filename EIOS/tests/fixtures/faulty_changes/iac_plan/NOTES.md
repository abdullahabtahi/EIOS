# iac_plan overlay

Adds `infra/broken/main.tf`, a well-formatted definition referencing an undeclared resource, so `terraform fmt -check` passes and `terraform validate` fails for that directory only.
