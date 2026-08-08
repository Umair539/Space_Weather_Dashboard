import streamlit as st
import os
import pandas as pd
import requests
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.logging_utils import setup_logger

logger = setup_logger("app", "app.log")


# This dashboard reads exclusively from the FastAPI layer (api/) - it holds
# no database connection at all. That is the point of this version: it
# exercises every endpoint the React frontend will use, so the API can be
# verified against a real client before that frontend is built. It isn't
# intended for production deployment, since running both services costs
# roughly double for a UI the React app replaces.
def api_base_url():
    url = os.environ.get("API_BASE_URL")
    if not url:
        # st.secrets raises when there's no secrets.toml rather than
        # returning the default, and this repo doesn't ship one - so the
        # localhost fallback is unreachable without catching that. Kept as
        # a lookup at all because Streamlit Cloud has no other way to set
        # config; locally, .env.{env} or the default covers it.
        try:
            url = st.secrets.get("API_BASE_URL")
        except Exception:
            url = None
    return (url or "http://localhost:8000").rstrip("/")


# 60s is deliberately shorter than every poll interval in api/db.py (30-300s)
# so this layer never becomes the reason data looks stale - the API's own
# cache is the real one, this just avoids re-requesting on every rerun and
# on every 120s fragment refresh.
@st.cache_data(ttl=60, show_spinner=False)
def api_get(path, params=None):
    try:
        response = requests.get(f"{api_base_url()}{path}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"API request failed for {path}: {e}")
        st.error(
            f"Could not reach the API at {api_base_url()}. "
            "Start it with `run_api` or set API_BASE_URL."
        )
        st.stop()


def api_dataframe(path, params=None):
    # Every endpoint returns "time" as an ISO string; the charts and the
    # date formatting in the views both need real timestamps.
    frame = pd.DataFrame(api_get(path, params))
    if not frame.empty:
        frame["time"] = pd.to_datetime(frame["time"])
    return frame


@st.cache_data(ttl=120, show_spinner=False)
def data_last_synced():
    # /health reports each table's true last-changed time: the ETL's upsert
    # only bumps updated_at when a value actually differs, so this moves
    # only on real changes. The old metadata.last_synced was rewritten on
    # every ETL run whether anything changed or not, and is deliberately
    # not exposed by the API.
    try:
        tables = api_get("/health")["tables"]
        stamps = [t["last_updated_at"] for t in tables.values() if t["last_updated_at"]]
        latest = max(pd.to_datetime(stamps))
        return f"Data last updated at {latest.strftime('%d %b, %H:%M')} UTC"
    except Exception:
        return "Error fetching last updated"


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


@st.cache_data(ttl=3600)
def get_noaa_advisory():
    url = "https://services.swpc.noaa.gov/text/advisory-outlook.txt"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        full_text = response.text

        if "**** SPACE WEATHER OUTLOOK ****" in full_text:
            content = full_text.split("**** SPACE WEATHER OUTLOOK ****")[-1]
            return content.strip()
        if not full_text.strip():
            return "Advisory temporarily unavailable."
        return full_text
    except Exception:
        return "Advisory temporarily unavailable."
