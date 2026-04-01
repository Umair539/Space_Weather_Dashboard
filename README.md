# Space Weather Dashboard

The goal of this project was to create a real-time space weather dashboard, a useful tool that provides people and organizations time to prepare for severe solar storms. This included creating a full ETL pipeline for space weather data with extraction, transformation and loading phases. The ETL pipeline was followed by an interactive web application developed using Streamlit.

[Live Dashboard Link](https://spaceweatherdashboard.streamlit.app/)

---
## Core Logic

This project is engineered as a decoupled system where data ingestion and visualisation operate independently to ensure high availability and UI responsiveness.

### 1. Automated ETL Pipeline
* **Extract:** Pulls near-real-time JSON data from NOAA API endpoints.
* **Transform:** Uses Pandas to clean, align, and transform datasets.
* **Load:** Saves data to a serverless PostgreSQL database hosted on Neon  using a "drop-and-swap" method to ensure zero downtime.

### 2. Background Worker (Threading)
* The app uses Python's `threading` module to run the ETL pipeline as a background process.
* The ETL runs every 60 seconds without freezing the user interface.
* This keeps the dashboard responsive while data processing happens behind the scenes.

### 3. Interactive Dashboard
* **Interactive Controls:** Uses sliders and dropdowns to let users filter date ranges and toggle between different space weather metrics.
* **Dynamic Querying:** Uses SQLAlchemy to pull only the data required for the user's current view based on what user has filtered, keeping the app lightweight.
* **Auto-Refresh:** Automatically updates the charts to show the newest data from the background pipeline without a manual reload.

### 4. Scheduled Orchestration
* **Github Actions** is used to trigger the ETL pipeline every 3 days to update the Neon database in the event the Streamlit app isn't in use.
* As the NOAA API endpoints only provide a weeks worth of data, this ensures that there wont be any period of missing data in the database.
---
## Data Source and Description
The data used in this project is retrieved from the [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov) which is the  most reliable source of space weather data available. Each successful extraction retrieves the last week's worth of data, making it a suitable source for real-time analysis.

The data used can be seen in the table below

| Dataset | Resolution | Length | Primary Features Used | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Dst Index** | Hourly | 7 days | `time_tag`, `dst` | `dst` is the target variable. |
| **Kp Index** | 3-Hourly | 7 days | `time_tag`, `Kp` | Features like `a_running` and `station_count` were available but not used. |
| **Solar Wind Magnetometer** | Minute | 7 days | `time_tag`, `bt`, `bz_gsm` | Features like `by_gsm` and `bx_gsm` were available but not used. |
| **Solar Wind Plasma** | Minute | 7 days | `time_tag`, `speed`, `density`, `temperature` | All primary features were used. |

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
6. Run the ETL pipeline
    ```
   run_etl
   ```
7. Run the Streamlit app (This also starts the background ETL automatically)
    ```
    run_app
   ```
8. Run tests
    ```
    run_tests
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

---

## Future Work

 - Improve test coverage
 - Incorporate real-time sunspot data
 - Using real-time solar wind and sunspot data, provide real-time predictions for the Dst Index using a machine learning model
 - ~~Improve real-time performance by making the app and ETL pipeline run together instead of running in separate terminals~~
 - ~~Deploy app on Streamlit Community Cloud~~
  
---

## Challenges

 - Getting flake8 linting to work as the black formatter sometimes disagreed with flake8
 - Unsure on how to implement more complex testing
 - It was difficult to produce the guage chart for the Kp index on the app homepage
