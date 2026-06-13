# download aws plugin
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# which cloud provider and location
provider "aws" {
  region = var.aws_region
}

# use default vpc
data "aws_vpc" "default" {
  default = true
}

# find all subnets inside default vpc
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# find latest amazon linux arm64 image (for t4g Graviton2)
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"] # '*' wildcard incase of update
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

# ecr repository for streamlit app docker image
resource "aws_ecr_repository" "app" {
  name                 = var.ecr_repo_app
  image_tag_mutability = "MUTABLE" # to overwrite latest on each push
  force_delete         = true
}

# ecr lifecycle policy
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the last 1 image"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 1
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# JSON policy doc for who can use this role (EC2)
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# Create IAM role for EC2 to use
resource "aws_iam_role" "ec2_ecr_role" {
  name               = "space-weather-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

# Attach ECR read-only access to EC2 role
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_ecr_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Attach SSM core policy so Session Manager replaces SSH
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_ecr_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Package role into instance profile so EC2 can use it
# Similar idea to packaging code into a container before deployment
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "space-weather-ec2-profile"
  role = aws_iam_role.ec2_ecr_role.name
}

# security group firewall rules for EC2 instance
resource "aws_security_group" "app" {
  name   = "space-weather-app-sg"
  vpc_id = data.aws_vpc.default.id

  ingress {
    description = "HTTP connection to Cloudflare"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS - Certbot"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0 # all ports
    to_port     = 0
    protocol    = "-1" # all protocols
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Set up EC2 server running streamlit app
resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2023.id # latest arm64 AMI
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]           # first default subnet
  vpc_security_group_ids = [aws_security_group.app.id]               # attach firewall rules
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name # attach ECR + SSM access

  # script running on EC2 launch
  user_data = templatefile("${path.module}/user_data.yaml", {
    db_url = var.database_read_url
  })

  root_block_device {
    volume_size = 8
  }

  tags = {
    Name = "space-weather-app"
  }
}

# static public IP
resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
}

# current AWS account ID (avoids hardcoding)
data "aws_caller_identity" "current" {}

# GitHub OIDC provider - lets GitHub Actions assume AWS roles without long-lived keys
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# Trust policy - only this repo's main branch can assume the role
data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:*"]
    }
  }
}

resource "aws_iam_role" "github_actions_app" {
  name               = "space-weather-github-actions-app"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}

# Permissions the deploy workflow needs
data "aws_iam_policy_document" "github_actions_app_policy" {
  # ECR login (account-level)
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # ECR push to the app repo
  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = [aws_ecr_repository.app.arn]
  }

  # Find the EC2 instance by tag
  statement {
    actions   = ["ec2:DescribeInstances"]
    resources = ["*"]
  }

  # Run commands on the EC2 instance via SSM
  statement {
    actions   = ["ssm:SendCommand"]
    resources = [
      "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript",
      "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:instance/*",
    ]
  }

  # Poll command status (needed after send-command)
  statement {
    actions   = ["ssm:GetCommandInvocation"]
    resources = ["arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"]
  }
}

resource "aws_iam_role_policy" "github_actions_app" {
  name   = "space-weather-github-actions-app-policy"
  role   = aws_iam_role.github_actions_app.id
  policy = data.aws_iam_policy_document.github_actions_app_policy.json
}