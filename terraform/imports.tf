# Declarative imports (Terraform 1.5+) - the same mappings that used to be
# a list of `terraform import` CLI commands, but run as part of a normal
# `terraform plan` / `terraform apply` instead of ~20 separate invocations.
# Terraform links each of these to the real resource on the next plan, then
# forgets about the block - safe to leave in place afterwards, or delete
# once everything shows up clean in `terraform state list`.
#
# aws_iam_openid_connect_provider.github_actions is deliberately NOT
# imported here - it only exists in the resource graph at all when
# create_oidc_provider = true (default: false, since one already exists on
# this account - see existing_oidc_provider_arn). If you do flip that on,
# add:
#   import {
#     to = aws_iam_openid_connect_provider.github_actions[0]
#     id = "arn:aws:iam::494487213442:oidc-provider/token.actions.githubusercontent.com"
#   }

import {
  to = aws_ecr_repository.etl
  id = "space-weather-etl"
}

import {
  to = aws_ecr_lifecycle_policy.etl
  id = "space-weather-etl"
}

import {
  to = aws_lambda_function.etl
  id = "space-weather-etl"
}

import {
  to = aws_cloudwatch_log_group.etl
  id = "/aws/lambda/space-weather-etl"
}

import {
  to = aws_iam_role.lambda_exec
  id = "space-weather-etl-role-xvrt45ud"
}

import {
  to = aws_iam_role_policy_attachment.lambda_basic_execution
  id = "space-weather-etl-role-xvrt45ud/arn:aws:iam::494487213442:policy/service-role/AWSLambdaBasicExecutionRole-61671f01-2d08-448f-b0ba-a78120b02073"
}

import {
  to = aws_iam_role.github_actions_deploy
  id = "github-actions-deploy-etl"
}

import {
  to = aws_cloudwatch_event_rule.etl_schedule
  id = "space-weather-etl-schedule"
}

import {
  to = aws_cloudwatch_event_target.etl_schedule
  id = "space-weather-etl-schedule/Id0f8846f8-c020-4c3b-b156-ac39ec593398"
}

import {
  to = aws_cloudwatch_event_rule.compact_ovation
  id = "compact-ovation"
}

import {
  to = aws_cloudwatch_event_target.compact_ovation
  id = "compact-ovation/Id04d3ba15-90e6-4004-9ed5-6b3dcee89157"
}

import {
  to = aws_sns_topic.alerts
  id = "arn:aws:sns:eu-west-2:494487213442:space-weather-etl-alerts"
}

import {
  to = aws_sns_topic_subscription.alerts_email[0]
  id = "arn:aws:sns:eu-west-2:494487213442:space-weather-etl-alerts:71c350ea-fa6e-4a00-8017-2a5f2b74627f"
}

import {
  to = aws_cloudwatch_metric_alarm.lambda_errors
  id = "space-weather-etl-errors"
}

import {
  to = aws_cloudwatch_log_metric_filter.schema_error
  id = "/aws/lambda/space-weather-etl:SchemaErrorFilter"
}

import {
  to = aws_cloudwatch_metric_alarm.schema_error
  id = "SchemaErrorAlarm"
}

import {
  to = aws_budgets_budget.monthly
  id = "494487213442:Monthly Cost Budget"
}

import {
  to = aws_s3_bucket.raw
  id = "space-weather-raw"
}

import {
  to = aws_s3_bucket_server_side_encryption_configuration.raw
  id = "space-weather-raw"
}

import {
  to = aws_s3_bucket_public_access_block.raw
  id = "space-weather-raw"
}

import {
  to = aws_cloudwatch_dashboard.etl
  id = "space-weather-etl-lambda"
}

import {
  to = cloudflare_r2_bucket.ovation
  id = "67e2c43a7c62257588605b51541a1caa/space-weather-prod"
}

# Per-source silence alarms - one per *existing* source. "ovation" is
# deliberately excluded: FetchAlarm-ovation doesn't exist live yet, apply
# creates it fresh.
import {
  to = aws_cloudwatch_metric_alarm.source_silence["mag"]
  id = "FetchAlarm-mag"
}

import {
  to = aws_cloudwatch_metric_alarm.source_silence["plasma"]
  id = "FetchAlarm-plasma"
}

import {
  to = aws_cloudwatch_metric_alarm.source_silence["dst"]
  id = "FetchAlarm-dst"
}

import {
  to = aws_cloudwatch_metric_alarm.source_silence["kp"]
  id = "FetchAlarm-kp"
}

import {
  to = aws_cloudwatch_metric_alarm.source_silence["ssn"]
  id = "FetchAlarm-ssn"
}

import {
  to = aws_cloudwatch_metric_alarm.source_silence["smoothed_ssn"]
  id = "FetchAlarm-smoothed_ssn"
}
