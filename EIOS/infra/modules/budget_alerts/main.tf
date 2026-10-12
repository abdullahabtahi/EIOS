resource "google_monitoring_notification_channel" "email" {
  display_name = "budget-alerts-${var.environment}"
  type         = "email"
  labels = {
    email_address = var.notification_email
  }
}

resource "google_billing_budget" "budget" {
  billing_account = var.billing_account
  display_name    = "budget-${var.environment}"

  amount {
    specified_amount {
      currency_code = var.currency_code
      units         = tostring(var.amount)
    }
  }

  dynamic "threshold_rules" {
    for_each = var.thresholds_percent
    content {
      threshold_percent = threshold_rules.value / 100.0
    }
  }
}
