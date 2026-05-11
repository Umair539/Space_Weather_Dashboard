# download aws plugin
terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
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
      name = "vpc-id"
      values = [data.aws_vpc.default.id]
    }
}

# find latest amazon linux arm image
data "aws_ami" "amazon_linux_2023_arm" {
    most_recent = true
    owners = ["amazon"]

    filter {
      name = "name"
      values = ["al2023-ami-*-arm64"] # '*' wildcard incase of update
    }

    filter {
      name = "architecture"
      values = ["arm64"]
    }
}

# ecr repository for streamlit app docker image
resource "aws_ecr_repository" "app" {
  name = var.ecr_repo_app
  image_tag_mutability = "MUTABLE" # to overwrite latest on each push
  force_delete = true
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

# who is allowed to assume IAM role 
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# IAM role for EC2 instance to pull from ECR
resource "aws_iam_role" "ec2_ecr_role" {
  name = "space-weather-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

# give ec2 role read-only access to ecr
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role = aws_iam_role.ec2_ecr_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# wrapper for ec2 to use IAM role
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "space-weather-ec2-profile"
  role = aws_iam_role.ec2_ecr_role.name
}

# security group firewall rules for EC2 instance
resource "aws_security_group" "app" {
  name = "space-weather-app-sg"
  vpc_id = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP for certbot challenge"
    from_port = 80
    to_port = 80
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    }

  ingress {
    description = "HTTPS"
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port = 0 # all ports
    to_port = 0
    protocol = "-1" # all protocols
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Set up EC2 server running streamlit app
resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2023_arm.id # latest ARM AMI
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0] # first default subnet
  vpc_security_group_ids = [aws_security_group.app.id] # attach firewall rules
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name # attach ECR access
  key_name               = var.key_pair_name # SSH key

  # script running on EC2 launch
  user_data = templatefile("${path.module}/user_data.sh", {
    aws_region   = var.aws_region
    image_uri    = "${aws_ecr_repository.app.repository_url}:latest"
    db_url       = var.database_read_url
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
  domain = "vpc"
}