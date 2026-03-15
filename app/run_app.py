import streamlit as st
import threading
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.run_etl import run_etl_pipeline


@st.cache_resource
def start_background_worker():
    thread = threading.Thread(target=run_etl_pipeline, daemon=True)
    thread.start()
    return thread


def main():

    st.set_page_config(
        page_title="Space Weather Dashboard",
        page_icon="🪐",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    home_page = st.Page("pages/home.py", title="Home")
    solar_wind_page = st.Page("pages/solar_wind.py", title="Solar Wind")
    geomag_indices_page = st.Page(
        "pages/geomag_indices.py", title="Geomagnetic Indices"
    )

    pg = st.navigation([home_page, solar_wind_page, geomag_indices_page])

    # launch etl pipeline in background using separate thread
    start_background_worker()

    if "noaa_data_db" not in st.session_state:
        st.session_state.noaa_data_db = st.connection(
            "noaa_data_db",
            type="sql",
            url="sqlite:///data/transformed/noaa_data.db?timeout=20",
        )  # timeout to prevent concurrent read/writes

    pg.run()


if __name__ == "__main__":
    main()
