import streamlit as st


def main():

    st.set_page_config(
        page_title="Space Weather Dashboard",
        page_icon="🪐",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    home_page = st.Page("views/home.py", title="Home", default=True)
    solar_wind_page = st.Page(
        "views/solar_wind.py", title="Solar Wind", url_path="solar-wind"
    )
    geomag_indices_page = st.Page(
        "views/geomag_indices.py",
        title="Geomagnetic Indices",
        url_path="geomagnetic-indices",
    )
    sun_page = st.Page(
        "views/sun.py", title="Solar Activity", url_path="solar-activity"
    )

    pg = st.navigation([home_page, solar_wind_page, geomag_indices_page, sun_page])

    pg.run()


if __name__ == "__main__":
    main()
