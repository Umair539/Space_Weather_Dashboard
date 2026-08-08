FROM python:3.11-slim

WORKDIR /app

COPY docker/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/

# Koyeb and Lightsail both inject PORT; the default keeps `docker run -p
# 8000:8000` working locally without setting anything.
ENV PORT=8000
EXPOSE 8000

# api.main:app, not api.main:launch - launch() is the local `run_api` entry
# point and exists only to parse --env and load a .env file. Deployed
# containers get DATABASE_READ_URL injected as a real env var instead, so
# python-dotenv isn't installed here at all.
#
# Deliberately one worker. The cache lives in this process's memory, so N
# workers would mean N independent copies, N sets of poll loops hitting
# Postgres, and responses that differ depending on which worker answered.
# Scale by adding instances behind a load balancer, not workers per
# instance - each instance is self-sufficient and read-only.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
