variable "project_id" { type = string }
variable "environment" { type = string }
variable "billing_account" { type = string }
variable "notification_email" { type = string }
variable "thresholds_percent" { type = list(number) }
variable "amount" { type = number }
variable "currency_code" { type = string }
