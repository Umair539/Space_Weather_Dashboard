terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Local state by default. Point this at an S3 backend (with a DynamoDB
  # lock table) before anyone but one person runs this, to avoid two
  # applies clobbering each other's state.
  #
  # backend "s3" {
  #   bucket         = "space-weather-terraform-state"
  #   key            = "etl/terraform.tfstate"
  #   region         = "eu-west-2"
  #   dynamodb_table = "space-weather-terraform-locks"
  #   encrypt        = true
  # }
}
