from pathlib import Path
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()
neon_db_url = os.environ.get("DATABASE_URL")


def data_last_synced():
    raw_data_path = Path("data/raw/dst.json").resolve()

    if raw_data_path.exists():
        mtime = raw_data_path.stat().st_mtime
        return datetime.fromtimestamp(mtime).strftime("%d %b, %H:%M")
    return "Error fetching last synced"


def safe_query(conn, query):
    try:
        return conn.query(query, ttl=60)
    except Exception:
        st.info("Error connecting to database. Please wait...")
        st.stop()


def init_db():
    if "neon_db" not in st.session_state:
        st.session_state.neon_db = st.connection(
            "neon_db",
            type="sql",
            url=neon_db_url,
        )  # timeout to prevent concurrent read/writes
    return st.session_state.neon_db
