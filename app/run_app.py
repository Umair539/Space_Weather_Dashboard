import streamlit as st


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
    sun_page = st.Page("pages/sun.py", title="Solar Activity")

    pg = st.navigation([home_page, solar_wind_page, geomag_indices_page, sun_page])

    pg.run()


if __name__ == "__main__":
    main()
