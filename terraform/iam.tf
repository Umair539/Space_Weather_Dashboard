# --- Lambda execution role ---
#
# Tightened from what's actually attached live (AmazonS3FullAccess - every
# bucket in the account, not just this Lambda's own - and an unscoped
# cloudwatch:PutMetricData). Verified safe to narrow: the Lambda's only
# other S3 touchpoint is fetch_rtsw.py's client against the public
# noaa-swpc-pds bucket, which uses UNSIGNED requests (no IAM credentials
# involved at all), so scoping to just S3_BUCKET doesn't affect it.
#
# Applying this only *adds* the scoped policy below - it does not detach
# AmazonS3FullAccess (Terraform never touches attachments it wasn't told to
# manage). See README.md "Tightening IAM" for the manual detach step and
# why it's manual and sequenced after this apply, not part of it.

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = var.lambda_exec_role_name
  # /service-role/ - the path the Lambda console's "create new role" flow
  # uses, not the default "/".
  path               = "/service-role/"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/service-role/${var.lambda_basic_execution_policy_name}"
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "lambda_scoped_permissions" {
  statement {
    sid       = "RawBucketReadWrite"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${var.s3_bucket_name}/*"]
  }

  statement {
    sid       = "RawBucketList"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.s3_bucket_name}"]
  }

  statement {
    sid       = "CustomMetrics"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"] # PutMetricData has no resource-level permissions
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["SpaceWeather"]
    }
  }
}

resource "aws_iam_role_policy" "lambda_scoped_permissions" {
  name   = "SpaceWeatherLambdaScopedAccess"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_scoped_permissions.json
}

# --- GitHub Actions OIDC (deploy_lambda.yml) ---

data "tls_certificate" "github_actions" {
  count = var.create_oidc_provider ? 1 : 0
  url   = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

resource "aws_iam_openid_connect_provider" "github_actions" {
  count = var.create_oidc_provider ? 1 : 0

  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github_actions[0].certificates[0].sha1_fingerprint]
}

locals {
  oidc_provider_arn = var.create_oidc_provider ? aws_iam_openid_connect_provider.github_actions[0].arn : var.existing_oidc_provider_arn
}

data "aws_iam_policy_document" "github_actions_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      # deploy_lambda.yml's job runs under `environment: prod` - the OIDC
      # token's sub claim reflects that environment, not the triggering
      # ref, so the trust condition matches on it rather than a branch.
      values = ["repo:${var.github_org}/${var.github_repo}:environment:${var.github_environment}"]
    }
  }
}

resource "aws_iam_role" "github_actions_deploy" {
  name               = var.github_deploy_role_name
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume.json
}

# Tightened from the live policy, which grants all of this as Resource:
# "*" - scoped here to the one repo and one function, the only ones this
# role has any business touching. Same as the Lambda role above: applying
# this creates a differently-named inline policy alongside the existing
# unscoped one rather than replacing it in place, so the old
# "github-actions-ecr-lambda" policy needs a manual removal once this is
# confirmed working - see README.md "Tightening IAM".
data "aws_iam_policy_document" "github_actions_deploy_permissions" {
  statement {
    sid       = "EcrAuth"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"] # required to be "*" - this action has no resource-level permissions
  }

  statement {
    sid = "EcrPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
    ]
    resources = [aws_ecr_repository.etl.arn]
  }

  statement {
    sid       = "UpdateLambdaCode"
    actions   = ["lambda:UpdateFunctionCode"]
    resources = [aws_lambda_function.etl.arn]
  }
}

resource "aws_iam_role_policy" "github_actions_deploy_scoped" {
  name   = "github-actions-ecr-lambda-scoped"
  role   = aws_iam_role.github_actions_deploy.id
  policy = data.aws_iam_policy_document.github_actions_deploy_permissions.json
}
