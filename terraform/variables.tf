# region to deploy resources to
variable "aws_region" {
  description = "AWS region"
  default     = "eu-west-2" # london
}

# ecr app repository name
variable "ecr_repo_app" {
  description = "ECR repository for Streamlit app docker image"
  default     = "space-weather-app"
}

# EC2 instance type
variable "instance_type" {
  description = "EC2 instance type"
  default     = "t3.micro"
}

# EC2 ssh key pair
variable "key_pair_name" {
  description = "Name of EC2 key pair for SSH access"
  type        = string
}

variable "database_read_url" {
  description = "Supabase read-only database connection string"
  type        = string
  sensitive   = true
}