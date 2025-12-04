import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

st_autorefresh(60000)

st.title("Space Weather Dashboard 🪐")

st.markdown(
    """
    This Space Weather Dashboard provides near real time data on key
    space environment properties, including solar wind parameters and
    geomagnetic indices, collected from the
    [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov).
    """
)

plasma = pd.read_csv("data/raw/plasma.csv")

st.markdown(
    f"Data last updated at {plasma['time_tag'].iloc[-1]}",
    unsafe_allow_html=True,
)

solar = pd.read_csv("data/transformed/solar_agg.csv")
solar.loc[:, "time"] = pd.to_datetime(solar["time"])

dst = pd.read_csv("data/transformed/dst.csv")
dst.loc[:, "time"] = pd.to_datetime(dst["time"])

kp = pd.read_csv("data/transformed/kp.csv")
kp.loc[:, "time"] = pd.to_datetime(kp["time"])


col1, col2, col3 = st.columns(3)

speed_delta = solar["speed_mean"].iloc[-2] / solar["speed_mean"].iloc[-3]
density_delta = solar["density_mean"].iloc[-2] / solar["density_mean"].iloc[-3]
temp_delta = solar["temperature_mean"].iloc[-2] / solar["temperature_mean"].iloc[-3]
pressure_delta = solar["pressure_mean"].iloc[-2] / solar["pressure_mean"].iloc[-3]
bz_delta = solar["bz_mean"].iloc[-2] / solar["bz_mean"].iloc[-3]
bt_delta = solar["bt_mean"].iloc[-2] / solar["bt_mean"].iloc[-3]
dst_delta = dst["dst"].iloc[-1] / dst["dst"].iloc[-2]
kp_delta = kp["Kp"].iloc[-1] / kp["Kp"].iloc[-2]

with col1:
    st.metric(
        label="Solar Wind Speed",
        value=f'{solar["speed_mean"].iloc[-2]} km/s',
        delta=(f"{round(speed_delta * 100 - 100, 2)}%"),
        border=True,
    )

    st.metric(
        label="Solar Wind Density",
        value=f'{solar["density_mean"].iloc[-2]} p/cm3',
        delta=(f"{round(density_delta * 100 - 100, 2)}%"),
        border=True,
    )

with col2:
    st.metric(
        label="Solar Wind Temperature",
        value=f'{solar["temperature_mean"].iloc[-2]} K',
        delta=(f"{round(temp_delta * 100 - 100, 2)}%"),
        border=True,
    )

    st.metric(
        label="Solar Wind Pressure",
        value=f'{solar["pressure_mean"].iloc[-2]} nPa',
        delta=(f"{round(pressure_delta * 100 - 100, 2)}%"),
        border=True,
    )

with col3:
    st.metric(
        label="IMF Bz",
        value=f'{solar["bz_mean"].iloc[-2]} nT',
        delta=(f"{round(bz_delta * 100 - 100, 2)}%"),
        border=True,
    )

    st.metric(
        label="IMF Bt",
        value=f'{solar["bt_mean"].iloc[-2]} nT',
        delta=(f"{round(bt_delta * 100 - 100, 2)}%"),
        border=True,
    )

c1, c2 = st.columns(2)

with c1:
    st.metric(
        label="Dst Index",
        value=f'{dst["dst"].iloc[-1]} nT',
        delta=(f"{round(dst_delta * 100 - 100, 2)}%"),
        border=True,
    )

with c2:
    st.metric(
        label="Kp Index",
        value=f'{kp["Kp"].iloc[-1]} nT',
        delta=(f"{round(kp_delta * 100 - 100, 2)}%"),
        border=True,
    )
