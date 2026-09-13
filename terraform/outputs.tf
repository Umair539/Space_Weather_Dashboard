output "lambda_function_arn" {
  value = aws_lambda_function.etl.arn
}

output "ecr_repository_url" {
  value = aws_ecr_repository.etl.repository_url
}

output "github_actions_deploy_role_arn" {
  description = "Set this as the ROLE_ARN repo/environment variable used by deploy_lambda.yml."
  value       = aws_iam_role.github_actions_deploy.arn
}

output "sns_alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "r2_bucket_name" {
  value = cloudflare_r2_bucket.ovation.name
}
