from pathlib import Path
from datetime import datetime
import streamlit as st


def data_last_synced():
    db_path = Path("data/raw/dst.json").resolve()

    if db_path.exists():
        mtime = db_path.stat().st_mtime
        return datetime.fromtimestamp(mtime).strftime("%d %b, %H:%M")
    return "Error fetching last synced"


def safe_query(conn, query):
    try:
        return conn.query(query, ttl=60)
    except Exception:
        st.info("Error connecting to database. Please wait...")
        st.stop()


def init_db():
    if "noaa_data_db" not in st.session_state:
        st.session_state.noaa_data_db = st.connection(
            "noaa_data_db",
            type="sql",
            url="sqlite:///data/transformed/noaa_data.db?timeout=20",
        )  # timeout to prevent concurrent read/writes
    return st.session_state.noaa_data_db
