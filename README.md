# Space Weather Dashboard

The goal of this project was to create a real-time space weather dashboard, a useful tool that provides people and organizations time to prepare for severe solar storms. This included creating a full ETL pipeline for space weather data with extraction, transformation and loading phases. The ETL pipeline was followed by an interactive web application developed using Streamlit and deployed onto Streamlit Community Cloud.

[Live Dashboard Link](https://spaceweatherdashboard.streamlit.app/)

**Note:** The app and database are hosted on free tiers and may need a moment to wake up on first load.

---
## Core Logic

This project is engineered as a decoupled system where data ingestion and visualisation operate independently to ensure high availability and UI responsiveness.

### 1. Automated ETL Pipeline
* **Extract:** Pulls near-real-time JSON data from NOAA API endpoints.
* **Transform:** Uses Pandas to clean, align, and transform datasets.
* **Load:** Appends new data to a serverless PostgreSQL database hosted on Neon as well as replacing the previous 24 hours of data to account for any updates at source.
* **Fault Tolerant:** The pipeline is resilient at every stage. Extraction failures do not affect the transform step, which reads from locally saved raw data. Transform failures do not affect the dashboard, which reads from the cloud database. In the event of database failure, raw data persisted in the GitHub repository ensures the database can be fully reproduced.
* **Schema Flexible:** Handles format changes in NOAA API responses. After observing the Dst and Kp Index endpoints switching from a list of lists to a list of dictionaries format, format detection was introduced at extraction time to parse either structure correctly. The pipeline is also forward-compatible with future switches between the two formats.

### 2. Real-Time ML Inference
* A trained CNN model generates real-time Dst Index predictions at the end of each ETL cycle using full hourly aggregations.
* Predictions are stored alongside the processed data, making them immediately available to the dashboard without any additional latency.
* The model was trained on historical space weather data as part of a Final Year Project at university. For full details on the architecture, training process, and evaluation, see the [dissertation repository](https://github.com/Umair539/Dissertation).
* The trained Keras model was converted to ONNX format, removing the TensorFlow dependency so that the memory consumption of the deployed app would be significantly reduced.

### 3. Background Worker (Threading)
* The app uses Python's `threading` module to run the ETL pipeline as a background process.
* The ETL runs every 60 seconds without freezing the user interface.

### 4. Interactive Dashboard
* **Interactive Controls:** Uses sliders and dropdowns to let users filter date ranges and toggle between different space weather metrics.
* **Dynamic Querying:** Uses dynamic SQL queries to pull only the data required for the user's current view based on what user has filtered, keeping the app lightweight.
* **Auto-Refresh:** Automatically updates the charts to show the newest data from the background pipeline without a manual reload.

### 5. Scheduled Orchestration
* **GitHub Actions** is used to trigger the ETL pipeline every 3 days to update the raw data and Neon database in the event the Streamlit app isn't in use. As the deployed app operates on a cloned repository, GitHub Actions is the only mechanism capable of updating the raw data.
* As NOAA API endpoints only provide the last week of data, this ensures the database is kept up to date during periods of inactivity.
---
## Data Source and Description
The data used in this project is retrieved from the [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov) which is the most reliable source of space weather data available. Each successful extraction retrieves the latest data from NOAA, which is appended to the database to build a continuously growing historical record.

The data used can be seen in the table below

| Dataset | Resolution | Primary Features Used | Notes |
| :--- | :--- | :--- | :--- |
| **Dst Index** | Hourly | `time_tag`, `dst` | `dst` is the target variable. |
| **Kp Index** | 3-Hourly | `time_tag`, `Kp` | Features like `a_running` and `station_count` were available but not used. |
| **Solar Wind Magnetometer** | Minute | `time_tag`, `bt`, `bz_gsm`, `by_gsm`, `bx_gsm` | Features `lon_gsm` and `lat_gsm` were available but not used. |
| **Solar Wind Plasma** | Minute | `time_tag`, `speed`, `density`, `temperature` | All primary features were used. |
| **Sunspots** | Daily | `time_tag`, `ssn` | — |
| **Predicted Solar Cycle** | Monthly | `time_tag`, `predicted_ssn` | `predicted_ssn` represents the predicted 13-month smoothed SSN, required as part of model input. Not used for visualisation. |

---

## Instructions To Run Locally

1. Clone the repository
   ```Bash
   git clone https://github.com/Umair539/Space_Weather_Dashboard.git
   ```
2. Change directory to the project folder
      ```Bash
   cd Space_Weather_Dashboard
   ```
3. (Optional) Create virtual environment
   ```bash
   python -m venv .venv
   source .venv/scripts/activate    #windows
   source .venv/bin/activate        #mac
   ```
4. Install requirements
    ```bash
   pip install -r requirements.txt
   ```
5. Install project in editable mode
    ```bash
   pip install -e .
   ```
6. Create a `.env` file in the project root with the following variables:
   ```env
   # Neon PostgreSQL — read/write connection for the ETL pipeline
   DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>/<dbname>

   # Read-only connection for the Streamlit app — can be set to the same value as DATABASE_URL
   DATABASE_READ_URL=postgresql+psycopg://<user>:<password>@<host>/<dbname>
   ```
7. Run the ETL pipeline
    ```
   run_etl
   ```
8. Run the Streamlit app (This also starts the background ETL automatically)
    ```
    run_app
   ```
The Streamlit app automatically updates every time a selection or the current page is changed, and also after 60 seconds of inactivity depending on the current page.

The ETL pipeline can also be configured to loop endlessly so that it can fetch real-time data. This can be toggled on or off in run_etl.py and/or in run_app.py by changing the loop variable to True/False.

If running ETL pipeline independently then inside run_etl.py modify:

```Python
def run_etl_pipeline(loop=False):
```
If running Streamlit app from run_app.py then modify the function argument:

```Python
thread = threading.Thread(target=run_etl_pipeline, args=(True,), daemon=True)
```