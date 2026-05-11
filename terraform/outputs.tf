output "elastic_ip" {
  description = "Point DuckDNS subdomain to elastic ip"
  value = aws_eip.app.public_ip
}

output "ecr_app_url" {
  description = "ECR URL for Streamlit app image"
  value = aws_ecr_repository.app.repository_url
}