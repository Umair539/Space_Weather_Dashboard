import streamlit as st
from pathlib import Path
from datetime import datetime


def data_last_synced():
    db_path = Path("data/transformed/noaa_data.db").resolve()

    if db_path.exists():
        mtime = db_path.stat().st_mtime
        return datetime.fromtimestamp(mtime).strftime("%d %b, %H:%M")
    return "Not Found"


def main():

    if "noaa_data_db" not in st.session_state:
        st.session_state.noaa_data_db = st.connection(
            "noaa_data_db",
            type="sql",
            url="sqlite:///data/transformed/noaa_data.db?timeout=20",
        )  # timeout to prevent concurrent read/writes

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

    pg.run()


if __name__ == "__main__":
    main()
