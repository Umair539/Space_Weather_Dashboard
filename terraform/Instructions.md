## Instructions

### Terminal
```bash
cd terraform
terraform apply -target=aws_ecr_repository.app -target=aws_ecr_lifecycle_policy.app -auto-approve
cd ..
aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin 494487213442.dkr.ecr.eu-west-2.amazonaws.com
docker build --provenance=false -t space-weather-app -f docker/app/Dockerfile .
docker tag space-weather-app:latest 494487213442.dkr.ecr.eu-west-2.amazonaws.com/space-weather-app:latest
docker push 494487213442.dkr.ecr.eu-west-2.amazonaws.com/space-weather-app:latest
cd terraform
terraform apply -auto-approve
```

### Cloudflare
- Update A record to new elastic IP from terraform output
- Set SSL to **Flexible**

### SSH
```bash
ssh -i ~/space-weather-key.pem ec2-user@<output-ip>
sudo certbot --nginx -d spaceweatherdashboard.com --non-interactive --agree-tos -m <your-email>
```

### Cloudflare
- Set SSL to **Full**