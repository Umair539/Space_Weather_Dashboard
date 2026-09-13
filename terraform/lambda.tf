locals {
  # https://<account_id>.r2.cloudflarestorage.com - derived rather than a
  # separate variable, so it can't drift from cloudflare_account_id.
  r2_endpoint = "https://${var.cloudflare_account_id}.r2.cloudflarestorage.com"
}

resource "aws_cloudwatch_log_group" "etl" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "etl" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = var.lambda_image_uri
  memory_size   = var.lambda_memory_size
  timeout       = var.lambda_timeout

  environment {
    variables = {
      ENV                  = "prod"
      DATABASE_URL         = var.database_url
      S3_BUCKET            = var.s3_bucket_name
      R2_BUCKET            = var.r2_bucket_name
      R2_ENDPOINT          = local.r2_endpoint
      R2_ACCESS_KEY_ID     = var.r2_access_key_id
      R2_SECRET_ACCESS_KEY = var.r2_secret_access_key
    }
  }

  # deploy_lambda.yml pushes new images straight via `aws lambda
  # update-function-code` on every merge to main - Terraform only owns the
  # function's config, not which image digest is currently deployed.
  lifecycle {
    ignore_changes = [image_uri]
  }

  depends_on = [aws_cloudwatch_log_group.etl]
}
