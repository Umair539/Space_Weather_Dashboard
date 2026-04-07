import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()
neon_db_url = os.environ.get("DATABASE_URL") or st.secrets.get("DATABASE_URL")


def data_last_synced(conn):
    try:
        query = "SELECT last_synced FROM metadata"
        result = safe_query(conn, query)
        last_synced = result.iloc[0].iloc[0].strftime("%d %b, %H:%M")
        return f"Data last synced at {last_synced}"

    except Exception:
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
