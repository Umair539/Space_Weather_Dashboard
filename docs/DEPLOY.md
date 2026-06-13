## Deploy Runbook

### Terraform
```bash
cd terraform
terraform apply -auto-approve
```

### Verify instance is ready
```bash
aws ssm start-session --target $(terraform output -raw instance_id)
cloud-init status  # wait until: status: done
exit
```

### GitHub Actions
- Update `ROLE_ARN_APP` in the GitHub `prod` environment: `terraform output -raw github_actions_role_arn`
- Push to `main` (or manually trigger **Build & Deploy Streamlit App Container**)

### Cloudflare
- Update A record to `terraform output -raw elastic_ip`
- Set SSL to **Flexible**

### SSM (Certbot)
```bash
aws ssm start-session --target $(terraform output -raw instance_id)
sudo certbot --nginx -d spaceweatherdashboard.com --non-interactive --agree-tos -m <email>
```

### Cloudflare
- Set SSL to **Full**
