output "elastic_ip" {
  description = "Point Cloudflare A record to this elastic IP"
  value       = aws_eip.app.public_ip
}

output "ecr_app_url" {
  description = "ECR URL for Streamlit app image"
  value       = aws_ecr_repository.app.repository_url
}