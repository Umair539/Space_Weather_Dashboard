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
