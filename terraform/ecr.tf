resource "aws_ecr_repository" "etl" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE" # deploy_lambda.yml pushes/reuses the :latest tag

  # false to match the live repo. Scanning on push costs nothing extra on
  # basic scanning and is worth turning on - see README's suggested
  # follow-ups - just not bundled into this import-fidelity change.
  image_scanning_configuration {
    scan_on_push = false
  }
}

# Retain only the latest image - see docs/DECISIONS.md "Cost & Performance
# Optimisations": prevents silent storage accumulation from every push.
resource "aws_ecr_lifecycle_policy" "etl" {
  repository = aws_ecr_repository.etl.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        # Matches the live rule's description exactly - the policy field is
        # whole-value replace, not patchable, so any wording difference
        # here forces an unnecessary destroy+recreate of the policy itself
        # (harmless to images/repo either way, but avoidable).
        description = "keep latest image only"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 1
        }
        action = { type = "expire" }
      }
    ]
  })
}
