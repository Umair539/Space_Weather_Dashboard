# Two schedules share the one Lambda - see docker/etl/etl.py's handler().

resource "aws_cloudwatch_event_rule" "etl_schedule" {
  name                = "${var.project_name}-etl-schedule"
  description         = "Regular ETL run - no event payload, handler() runs the pipeline as normal"
  schedule_expression = var.main_schedule_expression
}

resource "aws_cloudwatch_event_target" "etl_schedule" {
  rule     = aws_cloudwatch_event_rule.etl_schedule.name
  arn      = aws_lambda_function.etl.arn
  role_arn = var.etl_schedule_event_role_arn
}

resource "aws_cloudwatch_event_rule" "compact_ovation" {
  name                = "compact-ovation"
  description         = "space weather etl compact ovation daily midnight"
  schedule_expression = var.compact_ovation_schedule_expression
}

resource "aws_cloudwatch_event_target" "compact_ovation" {
  rule     = aws_cloudwatch_event_rule.compact_ovation.name
  arn      = aws_lambda_function.etl.arn
  role_arn = var.compact_ovation_event_role_arn
  input    = jsonencode({ action = "compact_ovation" })
}
