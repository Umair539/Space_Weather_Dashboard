# Capstone Project
## Space Weather Dashboard

The goal of this project was to create a real-time space weather dashboard, a useful tool that provides people and organizations time to prepare for severe solar storms. This project demonstrates a full ETL pipeline with data extraction, transformation and loading phases. The ETL pipeline was followed by an interactive web application developed using Streamlit.

---
## Data
The data used in this project is retrieved from the [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov) which is the  most reliable source of space weather data available. Each successful extraction retrieves the last week's worth of data, making it a suitable source for real-time analysis.

---

## Instructions To Run

1. Clone the repository
   ```Bash
   git clone https://github.com/Umair539/Capstone.git
   ```
2. Change directory to the project folder
      ```Bash
   cd Capstone
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
7. Run the Streamlit app
    ```
    run_app
   ```
The Streamlit app automatically updates every time a selection or the current page is changed, and also after 30-60 seconds of inactivity depending on the current page.

The ETL pipeline can also be configured to loop endlessly so that it can fetch real-time data. This can be toggled on or off by changing the loop variable in run_etl.py to True/False.

```Python
loop = True
```
ETL pipeline continues to run every 60 seconds.

```Python
loop = False
```

ETL pipeline will run only once.

---

## Future Work

 - Improve test coverage
 - Incorporate real-time sunspot data
 - Using real-time solar wind and sunspot data, provide real-time predictions for the Dst Index using a machine learning model
 - Deploy app on Streamlit Community Cloud
  
---

## Challenges

 - Getting flake8 linting to work as the black formatter sometimes disagreed with flake8