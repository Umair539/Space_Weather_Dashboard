# Space Weather Dashboard — Decisions & Problems Solved

A record of real engineering decisions made and problems encountered and fixed.

---

## Architecture Evolution

At this point in the project, the ETL pipeline ran in two ways: a GitHub Actions workflow every 3 days committing updated raw data to the repo, and a background thread on the Streamlit app, running on Streamlit Community Cloud, that ran whenever the app was active to provide fresh data to users. A series of cascading problems then forced a near-complete infrastructure overhaul.

**1. TensorFlow crashes > ONNX**
The first major problem was segmentation faults and inotify errors in the deployed Streamlit app. Logs showed the majority of crashes occurred during model inference, the part of the pipeline importing Keras/TensorFlow. The Keras model was therefore converted into an ONNX model which was more lightweight but more importantly no longer required the TensorFlow library to run. This resulted in no more crashes but also significantly faster execution time.

**2. NOAA deprecating 7-day solar wind endpoints**
NOAA issued a deprecation notice for the two 7-day solar wind endpoints the pipeline relied on, replacing them with rolling 24-hour windows from a new multi-satellite source. Key changes:
- Rolling window dropped from 7 days to 24 hours, a 3-day frequency was no longer sufficient to avoid missing data
- New endpoints serve data from multiple satellites with overlapping timestamps, requiring satellite selection logic (`source`, `active` fields)
- Schema changes, different column names, additional metadata fields

This forced updates to ingestion, transformation, and scheduling.

**3. GitHub repo > Cloudflare R2, Neon > Supabase**
More frequent ETL runs meant more commits to the repo, clogging the commit history. Migrated raw data to Cloudflare R2 object storage (free egress, no commit noise). Also migrated the database from Neon to Supabase. Neon's serverless compute hour limit was becoming a real constraint with more frequent runs. Supabase has no compute hour limit; it has a 7-day inactivity pause instead, but frequent ETL runs keep it active automatically.

**4. 30-second R2 latency + 6-hour staleness**
With raw data now in R2, every background thread ETL run had ~30 seconds of latency due to R2 round trips. This wasn't a problem for background runs, but on first page load users were waiting for that ETL to complete before seeing fresh data. Combined with the GitHub Actions ETL now running on a 6-hour schedule, visitors could arrive to data up to 6 hours old.

**Attempted fix**: Remove background thread ETL and drop GitHub Actions ETL to 5-minute schedule.

**New problem**: GitHub Actions can't reliably run at 5-minute intervals, and was instead running roughly hourly.

**5. Lambda + EventBridge**
The obvious solution was a dedicated scheduler. Moved the ETL pipeline to AWS Lambda with EventBridge running every 15 minutes, guaranteed scheduling, independent of repo activity or app state. Chose AWS as the most familiar cloud provider. Migrated R2 to S3 at the same time to keep everything under one roof. At the data scale (low MBs), the cost difference was negligible, and it meant fewer environment variables and simpler infrastructure.

***Why 15 Minutes***
 
The 15-minute schedule was a tradeoff - frequent enough to keep the dashboard feeling live and useful, while keeping Lambda compute and data transfer costs across the full pipeline within free tier.

Part of this came from knowing how the data actually works. Despite being called Real-Time Solar Wind, each update already contains data that's 2-3 minutes old by the time it's published, due to transmission time from the spacecraft at L1 and ground station processing. Since some latency is already baked into the source, adding a little more through a 15-minute polling interval felt reasonable - users are always looking at near-recent data regardless.

**6. Streamlit Community Cloud > EC2**
Moved the app to a self-hosted EC2 instance to eliminate cold starts and allow for always-on availability. Co-locating app and DB in the same EU region had the additional benefit of reduced database latency.

---

## The Lambda Scaling Problem

The new Lambda setup worked well initially, running in ~60 seconds. Over the following weeks, duration crept up to ~90 seconds and memory usage grew in parallel, on track to exceed AWS free tier Lambda compute limits.

The root cause: Lambda was loading the entire raw JSON datasets into memory on every run. As data accumulated over time, the datasets grew continuously, so performance got worse every day.

**Fix 1 - Monthly S3 partitioning**
Replaced the monolithic `dicts.json` per folder with monthly partition files (`dicts/YYYY-MM.json`). Lambda now only reads the last 2 months of data per run. Memory usage became bounded regardless of how much historical data accumulates. Each folder also writes a `metadata.json` tracking which partition files exist.

This reduced memory significantly, but Lambda was still slow.

**Fix 2 - Vectorised `filter_source`**
Added granular logging to identify exactly where the time was going. The bottleneck was `filter_source` in `process_rtsw`, the function that selects which satellite row to use per timestamp in the RTSW (real time solar wind) data. It was implemented using `groupby().apply()` which was calling a Python function for every 2 rows in the RTSW data. So for 2 months of minute-increment data, that meant calling the function up to ~44,000 times per run for each of the 2 RTSW datasets.

The function was rewritten so that it used pandas boolean indexing: split into active/inactive DataFrames, compute validity masks vectorised across all rows, replace bad rows using index alignment. Also handles the edge case of timestamps that only exist in the inactive satellite's data.

Result locally: 2 minutes -> under 1 second for `filter_source`.

The Lambda function duration before and after the fix can be seen below.

![Lambda duration](./Lambda-Duration.png)

**Note:** The Lambda function has 1024mb of assigned memory.

**Combined result on Lambda:**

| Metric | Before | After | Improvement |
|---|---|---|---|
| Duration | ~90s | ~7s | 92% faster |
| Memory used | ~524MB | ~294MB | 44% reduction |
| GB-seconds/run | 90 | 7 | 92% reduction |
| Free tier headroom | ~4,400 runs/month | ~57,000 runs/month | 13x more headroom |

Lambda duration and memory are now stable, no longer growing with time.

---

## Other Architecture Decisions

### Security
- **AWS credentials** - GitHub Actions uses OIDC to assume an IAM role at runtime, no long-lived AWS keys stored
- **Instance access** - SSH removed. Port 22 closed on the security group. Access via AWS Systems Manager Session Manager; no inbound ports required. GitHub Actions deploy uses `ssm send-command`
- **DB read connection string** - stored on the EC2 instance, only accessible to the app
- **DB write connection string** - stored as a Lambda environment variable
- **Streamlit read-only DB role** - Streamlit only has SELECT permissions, no write access to the database
- **R2 credentials** - dev only, stored as GitHub Actions secrets for the dev ETL workflow
- **AWS root account** - IAM user with admin access used for day-to-day operations, root account not used
- **EC2 auto-recovery** - CloudWatch alarm on `StatusCheckFailed_System` triggers `ec2:recover` automatically on hardware failure. Provisioned in Terraform

### Cloudflare R2 as dev/backup
Dev ETL runs on GitHub Actions with R2 as raw storage. If prod S3 is ever lost, R2 serves as a backup source, which was an unpredicted benefit of having a separate ETL pipeline.

### Fully decoupled ETL pipeline
Load writes to storage, transform reads from storage. No data threading between stages:
```
fetch_live → load_raw → fetch_saved → transform → load_transformed
```

### ETL coupling: decoupled → coupled → decoupled

The pipeline has been through two architecture reversals on this.

Originally decoupled: `fetch_live` extracted from NOAA endpoints and wrote to storage, then separately `fetch_saved` read from storage to pass data into transform. Clean separation.

On the AWS migration, with no partitioning yet, `load_raw` was fetching the entire dataset from S3 just to append a few new rows, then `extract_saved_data` would immediately re-fetch the same full dataset to pass into transform. The data was already in memory. Coupled the stages to skip the redundant GET operation to reduce costs: pass the in-memory dataset straight into transform, only falling back to `extract_saved_data` if no new data came from the endpoint.

After monthly partitioning was introduced, this broke down. The model used for inference requires weeks of data minimum (168 full hourly aggregations). To handle a new month starting with only a day's worth of data, transform always fetches the last 2 partitions from storage. Since the partitioning logic is in `extract_saved_data` and not in the `extract_live_data` stage, there was no clean way to replicate that in-memory, therefore decoupled again.

The original coupling was a reasonable micro-optimisation at the time. Partitioning made it unworkable.

### Terraform for EC2 provisioning
Deliberate learning choice to gain IaC experience. Managing EC2, ECR, IAM, security groups, and networking in production via Terraform.

---

## Cost & Performance Optimisations

- **EC2 over ECS** - avoids the cost of an Application Load Balancer; a single `t4g.micro` runs Docker/nginx/Certbot directly
- **ECR lifecycle policy** - retain only the latest image, old images auto-deleted to prevent silent storage accumulation
- **CloudWatch log retention** - 30 days, not indefinite
- **AWS Budgets alerts** - spend visibility and early warning on free tier
- **24hr upsert window** (`upsert_hours`) - minimises data transferred to Supabase each run; doubles as a full-DB recovery lever
- **Streamlit caching** - reduces repeated DB queries, important on free tier
- **`del` after large datasets in ETL** - explicit cleanup after datasets are no longer needed; minor contribution to peak memory reduction