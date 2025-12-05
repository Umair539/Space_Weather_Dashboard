import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

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

solar = pd.read_csv("data/transformed/solar.csv")
solar.loc[:, "time"] = pd.to_datetime(solar["time"])

dst = pd.read_csv("data/transformed/dst.csv")
dst.loc[:, "time"] = pd.to_datetime(dst["time"])

kp = pd.read_csv("data/transformed/kp.csv")
kp.loc[:, "time"] = pd.to_datetime(kp["time"])

speed_delta = solar["speed"].iloc[-1] / solar["speed"].iloc[-2]
density_delta = solar["density"].iloc[-1] / solar["density"].iloc[-2]
temp_delta = solar["temperature"].iloc[-1] / solar["temperature"].iloc[-2]
pressure_delta = solar["pressure"].iloc[-1] / solar["pressure"].iloc[-2]
bz_delta = solar["bz"].iloc[-1] / solar["bz"].iloc[-2]
bt_delta = solar["bt"].iloc[-1] / solar["bt"].iloc[-2]
dst_delta = dst["dst"].iloc[-1] / dst["dst"].iloc[-2]
kp_delta = kp["Kp"].iloc[-1] / kp["Kp"].iloc[-2]

c1, c2 = st.columns((0.5, 0.5))

with c1:
    st.markdown("")
    st.markdown("")
    st.markdown(
        f'<div style="font-size: 24px; text-align: center;">Dst Index: {dst["dst"].iloc[-1]} nT</div>',
        unsafe_allow_html=True,
    )
    st.line_chart(
        data=dst.iloc[-24:],
        x="time",
        y="dst",
        x_label="Time",
        y_label="Dst (nT)",
        color="#ff0000",
    )


with c2:

    step_colours = [
        {"range": [0, 5.0], "color": "green"},
        {"range": [5.0, 7.0], "color": "orange"},
        {"range": [7.0, 9.0], "color": "red"},
    ]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=kp["Kp"].iloc[-1],
            number={
                "prefix": "Kp: ",
            },
            title={
                "text": "Kp Index",
                "font": {"size": 24},
            },
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 9]},
                "steps": step_colours,
                "bar": {"color": "rgba(0, 0, 0, 0)"},
                "threshold": {
                    "line": {"color": "black", "width": 3},
                    "value": kp["Kp"].iloc[-1],
                    "thickness": 1,
                },
            },
        )
    )

    fig.update_layout(
        height=400,
    )

    st.plotly_chart(fig, width="stretch")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Solar Wind Speed",
        value=f'{solar["speed"].iloc[-1]} km/s',
        delta=(f"{round(speed_delta * 100 - 100, 2)}%"),
        border=True,
    )

    st.metric(
        label="Solar Wind Density",
        value=f'{solar["density"].iloc[-1]} p/cm3',
        delta=(f"{round(density_delta * 100 - 100, 2)}%"),
        border=True,
    )

with col2:
    st.metric(
        label="Solar Wind Temperature",
        value=f'{solar["temperature"].iloc[-1]} K',
        delta=(f"{round(temp_delta * 100 - 100, 2)}%"),
        border=True,
    )

    st.metric(
        label="Solar Wind Pressure",
        value=f'{solar["pressure"].iloc[-1]} nPa',
        delta=(f"{round(pressure_delta * 100 - 100, 2)}%"),
        border=True,
    )

with col3:
    st.metric(
        label="IMF Bz",
        value=f'{solar["bz"].iloc[-1]} nT',
        delta=(f"{round(bz_delta * 100 - 100, 2)}%"),
        border=True,
    )

    st.metric(
        label="IMF Bt",
        value=f'{solar["bt"].iloc[-1]} nT',
        delta=(f"{round(bt_delta * 100 - 100, 2)}%"),
        border=True,
    )
