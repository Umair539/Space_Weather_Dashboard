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

solar = pd.read_csv("data/transformed/solar_agg.csv")
solar.loc[:, "time"] = pd.to_datetime(solar["time"])

dst = pd.read_csv("data/transformed/dst.csv")
dst.loc[:, "time"] = pd.to_datetime(dst["time"])

kp = pd.read_csv("data/transformed/kp.csv")
kp.loc[:, "time"] = pd.to_datetime(kp["time"])

plasma = pd.read_csv("data/raw/plasma.csv")

col1, col2, col3 = st.columns(3)

speed_delta = solar["speed_mean"].iloc[-2] / solar["speed_mean"].iloc[-3]
density_delta = solar["density_mean"].iloc[-2] / solar["density_mean"].iloc[-3]
temp_delta = solar["temperature_mean"].iloc[-2] / solar["temperature_mean"].iloc[-3]
pressure_delta = solar["pressure_mean"].iloc[-2] / solar["pressure_mean"].iloc[-3]
bz_delta = solar["bz_mean"].iloc[-2] / solar["bz_mean"].iloc[-3]
bt_delta = solar["bt_mean"].iloc[-2] / solar["bt_mean"].iloc[-3]

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
