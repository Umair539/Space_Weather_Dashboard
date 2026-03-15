from pathlib import Path
from datetime import datetime
import streamlit as st


def data_last_synced():
    db_path = Path("data/raw/dst.json").resolve()

    if db_path.exists():
        mtime = db_path.stat().st_mtime
        return datetime.fromtimestamp(mtime).strftime("%d %b, %H:%M")
    return "Not Found"


def safe_query(conn, query):
    try:
        return conn.query(query, ttl=60)
    except Exception:
        st.info("Error connecting to database. Please wait...")
        st.stop()
