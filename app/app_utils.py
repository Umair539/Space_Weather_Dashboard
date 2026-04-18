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


def data_last_synced(conn):
    try:
        query = "SELECT last_synced FROM metadata"
        result = safe_query(conn, query, 5)
        last_synced = result.iloc[0].iloc[0].strftime("%d %b, %H:%M")
        return f"Data last synced at {last_synced} UTC"

    except Exception:
        return "Error fetching last synced"


def safe_query(conn, query, ttl=60):
    try:
        return conn.query(query, ttl=ttl)
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
