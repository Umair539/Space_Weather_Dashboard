import streamlit as st
from dotenv import load_dotenv
import os
import requests
from datetime import datetime, timezone

load_dotenv()
neon_db_url = os.environ.get("DATABASE_URL") or st.secrets.get("DATABASE_URL")


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
    except Exception:
        st.info("Connecting to database. Please wait...")
        st.stop()


def init_db():
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


def is_data_fresh(conn):
    try:
        result = conn.query("SELECT last_synced FROM metadata", ttl=5)
        last_synced = result.iloc[0].iloc[0]
        age = (
            datetime.now(timezone.utc).replace(tzinfo=None) - last_synced
        ).total_seconds()
        return age < 180
    except Exception:
        return False
