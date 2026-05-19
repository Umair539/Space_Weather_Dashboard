# Space Weather Dashboard

## Motivation

My [dissertation](https://github.com/Umair539/Dissertation) involved training and testing machine learning models with historical space weather data. After working with static data, I wanted to gain experience working with live, frequently updated data, building something that continuously ingests, transforms, and delivers data to a frontend application.

Space weather was a natural fit. Having studied it through my dissertation, and with astronomy being a genuine interest of mine, it made sense to keep working in the same domain. What started as a way to gain experience ended up growing into a full production-grade AWS pipeline with automated orchestration, ML inference, and a live dashboard.

**Live Dashboard Link:** https://spaceweatherdashboard.com

---

## Tech Stack

**AWS** (Lambda · ECR · EventBridge · S3 · CloudWatch · SNS · IAM · EC2) · **Streamlit** · **Supabase** (PostgreSQL database) · **Pandas** · **Keras / TensorFlow** · **GitHub Actions** · **Python** · **Docker** · **Terraform** · **Nginx** · **Cloudflare**

---

## Architecture

![Architecture](docs/architecture.svg)

---
## Core Logic

This project is engineered as a decoupled system where data ingestion and visualisation operate independently to ensure high availability and UI responsiveness.

### 1. Automated ETL Pipeline
* **Extract:** Pulls near-real-time JSON data from NOAA API endpoints.
* **Transform:** Uses Pandas to clean, align, and transform datasets.
* **Load:** Saves raw extracted JSON to AWS S3, then upserts transformed data into a serverless PostgreSQL database hosted on Supabase, replacing the previous 24 hours of data to account for any updates at source.
* **Fault Tolerant:** The pipeline is resilient at every stage. Extraction failures do not affect the transform step, which falls back to the latest raw data in S3. Transform failures do not affect the dashboard, which reads from the cloud database. In the event of database failure, raw data persisted in S3 ensures the database can be fully reproduced. A parallel dev pipeline running on GitHub Actions with a Cloudflare R2 bucket provides an additional layer of redundancy, if prod raw storage is lost, the dev pipeline's R2 bucket can serve as a backup source.
* **Schema Flexible:** Handles format changes in NOAA API responses. After observing the Dst and Kp Index endpoints switching from a list of lists to a list of dictionaries format, format detection was introduced at extraction time to parse either structure correctly. The pipeline is also forward-compatible with future switches between the two formats.

### 2. ML Inference

![Dst Predictions](docs/Dst-predictions.png)
* A CNN model trained using Keras / TensorFlow generates Dst Index predictions at the end of each ETL cycle using full hourly aggregations.
* Predictions are stored alongside the processed data, making them immediately available to the dashboard without any additional latency.
* The model was trained on historical space weather data as part of a Final Year Project at university. For full details on the architecture, training process, and evaluation, see the [dissertation repository](https://github.com/Umair539/Dissertation).
* The trained Keras model was converted to ONNX format, removing the TensorFlow dependency so that the memory consumption of the Lambda function would be significantly reduced.

### 3. Interactive Dashboard
* **Interactive Controls:** Uses radio buttons and dropdowns to let users filter date ranges (Last 24 Hours, Last Week, Last Month, etc.) and toggle between different space weather metrics.
* **Dynamic Querying:** Uses dynamic SQL queries to pull only the data required for the user's current view based on what user has filtered, keeping the app lightweight.
* **Auto-Refresh:** Automatically updates the charts to show the newest data from the scheduled pipeline without a manual reload.
* **Caching:** Query results are cached to minimise repeated database calls and avoid exceeding free tier limits.

### 4. Scheduled Orchestration
* The ETL pipeline is packaged as a Docker container, stored in **AWS ECR**, and deployed as an **AWS Lambda** function.
* **AWS EventBridge Scheduler** triggers the Lambda every 15 minutes, keeping both S3 and the database continuously up to date.
* **AWS CloudWatch** captures Lambda logs for monitoring and debugging each pipeline run.
* **AWS SNS** sends alarm notifications when the pipeline fails, enabling rapid incident response.
* **GitHub Actions** automates the deployment pipeline: on every push to main that changes relevant files, the Docker image is rebuilt, pushed to ECR, and the Lambda function is updated to use the latest image.
* As NOAA API endpoints only provide the last week of data, this ensures the database is kept up to date during periods of inactivity.

### 5. App Hosting

* The Streamlit frontend is containerised and self-hosted on an **AWS EC2 instance**, provisioned with **Terraform** and served over HTTPS via Nginx and Certbot.
* **Infrastructure as Code:** Terraform provisions the EC2 instance (`t3.micro`), ECR repository, IAM role, security group, and Elastic IP.
* **Automated Setup:** A `user_data.yaml` cloud-init config runs on first boot. It installs Docker and Nginx, authenticates with ECR via IAM role, pulls the app image, and starts the container.
* **Reverse Proxy:** Nginx forwards traffic from port 80/443 to the Streamlit container on port 8501.
* **TLS:** HTTPS provided by Certbot (Let's Encrypt). DNS managed via Cloudflare, pointed at the Elastic IP, serving the dashboard at https://spaceweatherdashboard.com
* **SSH Access:** Port 22 open on the security group for direct access to the instance.
* **CD:** GitHub Actions builds and pushes a new app image to ECR on every relevant push to `main`, then SSHs into the EC2 instance to pull the latest image and restart the container automatically.

### 6. Testing
* **Unit tests** cover all individual transform functions -- outlier filtering, missing data handling, source fallback logic, column filtering, pressure calculation, model inference helpers, and more.
* **Component tests** cover all transform orchestrators end to end -- `process_rtsw`, `process_dst`, `process_kp`, `process_ssn`, `prepare_model_inputs`, `model_inference`, and others.
* **Integration tests** run the full transform pipeline against a fixed fixture snapshot of real NOAA data, asserting schema, null counts and datetime index integrity.
* **99% coverage** across the transform layer, enforced by a coverage gate in CI.
* **CI gate** runs lint, unit, component, and integration tests on every push to `main` before the Docker build, blocking deploy on any failure.

### 7. Development Environment
* A parallel dev environment mirrors the production pipeline for testing purposes.
* The dev branch runs the pipeline on GitHub Actions (in contrast to AWS Lambda/EventBridge in prod), stores raw data in a Cloudflare R2 bucket, and writes to a separate dev Supabase instance, keeping test runs fully isolated from production data.
* The Streamlit frontend can also be run locally against the dev database for UI testing without affecting the live dashboard.

---
## Data Source and Description
The data used in this project is retrieved from the [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov) which is the most reliable source of space weather data available. Each successful extraction retrieves the latest data from NOAA, which is appended to the database to build a continuously growing historical record.

The data used can be seen in the table below

| Dataset | Resolution | Primary Features Used | Notes |
| :--- | :--- | :--- | :--- |
| **Dst Index** | Hourly | `time_tag`, `dst` | Quicklook (provisional) values. |
| **Kp Index** | 3-Hourly | `time_tag`, `Kp` | — |
| **Solar Wind Magnetometer** | Minute | `time_tag`, `bt`, `bz_gsm`, `by_gsm`, `bx_gsm` | — |
| **Solar Wind Plasma** | Minute | `time_tag`, `speed`, `density`, `temperature` | — |
| **Sunspots** | Daily | `Obsdate`, `swpc_ssn` | — |
| **Predicted Solar Cycle** | Monthly | `time-tag`, `predicted_ssn` | `predicted_ssn` represents the predicted 13-month smoothed SSN, required as part of model input. Not used for visualisation. |

## Documentation

- [Decisions & problems solved](docs/DECISIONS.md)
- [Deployment guide](docs/DEPLOYMENT.md)