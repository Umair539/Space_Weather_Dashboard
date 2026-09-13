# Prod-only bucket holding compacted OVATION output (ovation/YYYY/MM/DD.parquet)
# - the copy meant for repeated external reads, so it gets R2's free egress.
# The raw per-run OVATION files stay in S3 alongside the rest of the raw
# archive; only the daily compacted file goes here. See
# src/load/compact_ovation.py and the OVATION commit message for the split.
resource "cloudflare_r2_bucket" "ovation" {
  account_id = var.cloudflare_account_id
  name       = var.r2_bucket_name
  location   = var.r2_location == "" ? null : var.r2_location
}
