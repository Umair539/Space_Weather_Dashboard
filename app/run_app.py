import streamlit as st


def main():

    if "noaa_data_db" not in st.session_state:
        st.session_state.noaa_data_db = st.connection(
            "noaa_data_db",
            type="sql",
            url="sqlite:///data/transformed/noaa_data.db?timeout=20",
        )

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
