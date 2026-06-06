import streamlit as st
import os
import requests
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.logging_utils import setup_logger

logger = setup_logger("app", "app.log")


@st.cache_data(ttl=120)
def data_last_synced(_conn):
    # cached for 120s
    # ttl=0 on conn.query so @st.cache_data is the only caching layer
    try:
        result = _conn.query("SELECT last_synced FROM metadata", ttl=0)
        last_synced = result.iloc[0].iloc[0].strftime("%d %b, %H:%M")
        return f"Data last synced at {last_synced} UTC"
    except Exception:
        return "Error fetching last synced"


@st.cache_data(ttl=120)
def get_latest_timestamp(_conn, table):
    # cheap MAX(time) check cached for 120s
    # ttl=0 so conn.query doesn't add a second caching layer on top
    result = _conn.query(f"SELECT MAX(time) FROM {table}", ttl=0)
    return result.iloc[0, 0]


@st.cache_data
def cached_query(_conn, query, latest_ts):
    # cached forever until version MAX(time) changes
    # conn.query ttl=0 because @st.cache_data already guarantees this only
    # runs on a cache miss, so there's nothing for conn.query to cache
    try:
        return _conn.query(query, ttl=0)
    except Exception as e:
        st.info("Connecting to database. Please wait...")
        logger.error(f"Database query failed: {e}")
        st.stop()


def init_db():
    neon_db_url = os.environ.get("DATABASE_READ_URL") or st.secrets.get(
        "DATABASE_READ_URL"
    )
    return st.connection(
        "neon_db",
        type="sql",
        url=neon_db_url,
    )


def github_link():
    st.markdown(
        """<div>
    <a href="https://github.com/Umair539/Space_Weather_Dashboard" target="_blank" style="color:#8b949e;">
        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8"/>
        </svg>
    </a></div>""",
        unsafe_allow_html=True,
    )


def get_noaa_advisory():
    url = "https://services.swpc.noaa.gov/text/advisory-outlook.txt"
    try:
        response = requests.get(url)
        response.raise_for_status()
        full_text = response.text

        if "**** SPACE WEATHER OUTLOOK ****" in full_text:
            content = full_text.split("**** SPACE WEATHER OUTLOOK ****")[-1]
            return content.strip()
        return full_text
    except Exception as e:
        return f"Error fetching advisory: {e}"
