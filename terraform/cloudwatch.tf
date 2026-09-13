resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-etl-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Lambda crash - fires on function errors.
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-etl-errors"
  alarm_description   = "ETL Lambda invocation errored"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.etl.function_name }
  statistic           = "Sum"
  period              = 900
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "missing"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# Per-source silence - fires if a source hasn't fetched fresh data in an
# hour. Missing data points count as breaching: no metric at all is exactly
# what "stopped fetching" looks like, so it must alarm rather than be
# ignored. This is what caught the NOAA WAF issue (docs/DECISIONS.md).
resource "aws_cloudwatch_metric_alarm" "source_silence" {
  for_each = toset(var.fetch_sources)

  alarm_name          = "FetchAlarm-${each.key}"
  alarm_description   = "${each.key}: no successful fetch in the last hour"
  namespace           = "SpaceWeather"
  metric_name         = "SuccessfulFetch"
  dimensions          = { Source = each.key }
  statistic           = "Sum"
  period              = var.silence_alarm_period_seconds
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# Schema change - src/utils/validator.py raises SchemaError, which the
# except-block logging in fetch_utils.py surfaces as a log line. This
# filter turns the literal string "SchemaError" appearing in the Lambda's
# logs into a metric, rather than the pipeline code calling PutMetricData
# directly the way SuccessfulFetch does.
resource "aws_cloudwatch_log_metric_filter" "schema_error" {
  name           = "SchemaErrorFilter"
  log_group_name = aws_cloudwatch_log_group.etl.name
  pattern        = "SchemaError"

  metric_transformation {
    name          = "SchemaErrorCount"
    namespace     = "SpaceWeather"
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "schema_error" {
  alarm_name          = "SchemaErrorAlarm"
  namespace           = "SpaceWeather"
  metric_name         = "SchemaErrorCount"
  statistic           = "Sum"
  period              = 900
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  depends_on = [aws_cloudwatch_log_metric_filter.schema_error]
}

# Single-widget dashboard tracking Lambda duration - matches the live
# dashboard body exactly (found via the account-wide sweep, wasn't in this
# config before).
resource "aws_cloudwatch_dashboard" "etl" {
  dashboard_name = "space-weather-etl-lambda"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 6
        height = 6
        properties = {
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.etl.function_name]
          ]
          region = var.aws_region
        }
      }
    ]
  })
}
