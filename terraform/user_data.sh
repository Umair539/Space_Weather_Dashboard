#!/bin/bash
# bash script
set -e # stop if any issues

# Update OS and install dependencies
dnf update -y
dnf install -y docker nginx python3-certbot-nginx

# Start Docker and enable it to start on reboot
systemctl enable docker
systemctl start docker

# Log in to ECR so Docker can pull the image
# get-login-password for temp credentials for docker to use to sign into ECR
aws ecr get-login-password --region ${aws_region} \
  | docker login --username AWS --password-stdin \
    $(echo ${image_uri} | cut -d/ -f1)

# Pull the Streamlit app image from ECR
docker pull ${image_uri}

# Write the database URL to an env file
# chmod 600 = only the owner can read it
cat > /home/ec2-user/.env <<EOF
DATABASE_READ_URL=${db_url}
EOF
chmod 600 /home/ec2-user/.env

# Run the Streamlit container
# -d = run in background
# --restart unless-stopped = restart on crash or reboot
# --env-file = pass in the database URL
# -p 8501:8501 = map container port to host port
docker run -d \
  --name space-weather-app \
  --restart unless-stopped \
  --env-file /home/ec2-user/.env \
  -p 8501:8501 \
  ${image_uri}

# Configure nginx to forward port 80 traffic to Streamlit on port 8501
# Upgrade headers are needed for Streamlit's WebSocket connection
cat > /etc/nginx/conf.d/streamlit.conf <<'EOF'
server {
    listen 80;
    server_name spaceweatherdashboard.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
EOF

# Start nginx and enable it to start on reboot
systemctl enable nginx
systemctl start nginx