locals {
  budget_notify_email = var.budget_alert_email != "" ? var.budget_alert_email : var.alert_email
}

# NOTE: the live budget also excludes Credit/Refund record types via a
# billing-view filter expression that the aws_budgets_budget resource can't
# fully represent (it only supports simple positive cost_filter dimensions,
# not an exclusion). Importing this resource is therefore expected to show
# a small permanent diff on that filter - not a sign anything else is wrong.
resource "aws_budgets_budget" "monthly" {
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = var.monthly_budget_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = local.budget_notify_email == "" ? [] : [1]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = 80
      threshold_type             = "PERCENTAGE"
      notification_type          = "FORECASTED"
      subscriber_email_addresses = [local.budget_notify_email]
    }
  }

  dynamic "notification" {
    for_each = local.budget_notify_email == "" ? [] : [1]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = 100
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [local.budget_notify_email]
    }
  }
}
