import streamlit as st
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
from utils import safe_query, data_last_synced, init_db
import altair as alt

init_db()
conn = st.session_state.noaa_data_db

st.title("Space Weather Dashboard 🪐")

st.markdown(
    """
    This Space Weather Dashboard provides near real time data on key
    space environment properties, including solar wind parameters and
    geomagnetic indices, collected from the
    [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov).
    """
)

st.markdown(
    f"<div style='text-align: right; font-style: italic; color: gray;'>"
    f"Data last synced at {data_last_synced()}"
    f"</div>",
    unsafe_allow_html=True,
)

solar = safe_query(conn, "SELECT * FROM solar ORDER BY time DESC LIMIT 61")
dst = safe_query(conn, "SELECT * FROM dst ORDER BY time DESC LIMIT 24")
kp = safe_query(conn, "SELECT * FROM kp ORDER BY time DESC LIMIT 1")


#
speed_delta = solar["speed"].iloc[0] / solar["speed"].iloc[60]
density_delta = solar["density"].iloc[0] / solar["density"].iloc[60]
temp_delta = solar["temperature"].iloc[0] / solar["temperature"].iloc[60]
pressure_delta = solar["pressure"].iloc[0] / solar["pressure"].iloc[60]
bz_delta = solar["bz"].iloc[0] / solar["bz"].iloc[60]
bt_delta = solar["bt"].iloc[0] / solar["bt"].iloc[60]

c1, c2 = st.columns((0.5, 0.5))

with c1:
    st.markdown("")
    st.markdown(
        f'<div style="font-size: 24px; text-align: center; margin-top: 20px;">'
        f'Dst Index: {dst["dst"].iloc[0]} nT</div>',
        unsafe_allow_html=True,
    )

    dst_chart = (
        alt.Chart(dst)
        .mark_line(color="#ff0000")
        .encode(
            x=alt.X(
                "time:T",
                axis=alt.Axis(
                    labelAngle=0,
                    tickCount=6,
                    format="%H:%M",
                    title="Time",
                ),
            ),
            y=alt.Y("dst:Q", title="Dst (nT)"),
        )
        .properties(height=350)
    )

    st.altair_chart(dst_chart, width="stretch")

with c2:
    step_colours = [
        {"range": [0, 5.0], "color": "green"},
        {"range": [5.0, 7.0], "color": "orange"},
        {"range": [7.0, 9.0], "color": "red"},
    ]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=kp["Kp"].iloc[0],
            number={"prefix": "Kp: "},
            title={"text": "Kp Index", "font": {"size": 24}},
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 9]},
                "steps": step_colours,
                "bar": {"color": "rgba(0, 0, 0, 0)"},
                "threshold": {
                    "line": {"color": "black", "width": 3},
                    "value": kp["Kp"].iloc[0],
                    "thickness": 1,
                },
            },
        )
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")

col1, col2, col3 = st.columns(3)

# Metrics
with col1:
    st.metric(
        label="Solar Wind Speed",
        value=f'{solar["speed"].iloc[0]} km/s',
        delta=(f"{round(speed_delta * 100 - 100, 2)}%"),
        border=True,
    )
    st.metric(
        label="Solar Wind Density",
        value=f'{solar["density"].iloc[0]} p/cm3',
        delta=(f"{round(density_delta * 100 - 100, 2)}%"),
        border=True,
    )

with col2:
    st.metric(
        label="Solar Wind Temperature",
        value=f'{solar["temperature"].iloc[0]} K',
        delta=(f"{round(temp_delta * 100 - 100, 2)}%"),
        border=True,
    )
    st.metric(
        label="Solar Wind Pressure",
        value=f'{solar["pressure"].iloc[0]} nPa',
        delta=(f"{round(pressure_delta * 100 - 100, 2)}%"),
        border=True,
    )

with col3:
    st.metric(
        label="IMF Bz",
        value=f'{solar["bz"].iloc[0]} nT',
        delta=(f"{round(bz_delta * 100 - 100, 2)}%"),
        border=True,
    )
    st.metric(
        label="IMF Bt",
        value=f'{solar["bt"].iloc[0]} nT',
        delta=(f"{round(bt_delta * 100 - 100, 2)}%"),
        border=True,
    )

st_autorefresh(60000)
