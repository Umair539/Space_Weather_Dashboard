# The raw/transformed data + OVATION run-file bucket. Previously only
# referenced by name via a variable - brought under management as-is
# (matches the live config exactly), no lifecycle rule added. The stale
# uncompressed-.json objects that once justified adding one have already
# been cleaned up (verified live 2026-08-31 - see memory), so there's
# nothing outstanding for a lifecycle rule to solve right now.
resource "aws_s3_bucket" "raw" {
  bucket = var.s3_bucket_name
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket = aws_s3_bucket.raw.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
