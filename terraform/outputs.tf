output "elastic_ip" {
  description = "Point Cloudflare A record to this elastic IP"
  value       = aws_eip.app.public_ip
}

output "ecr_app_url" {
  description = "ECR URL for Streamlit app image"
  value       = aws_ecr_repository.app.repository_url
}

output "github_actions_role_arn" {
  description = "Set this as ROLE_ARN_APP in GitHub Actions environment variables"
  value       = aws_iam_role.github_actions_app.arn
}

output "instance_id" {
  description = "EC2 instance ID for SSM sessions"
  value       = aws_instance.app.id
}