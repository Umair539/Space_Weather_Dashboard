import streamlit as st
import altair as alt
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

st_autorefresh(30000)
conn = st.session_state.noaa_data_db

st.title("Real Time Solar Wind Properties 🛰️")

col1, col2, col3 = st.columns(3)

with col1:
    resolution = st.selectbox(
        label="Select time resolution", options=["Minutely", "Hourly"], index=0
    )

columns = ["Speed", "Density", "Temperature", "Pressure", "Bz", "Bt"]

with col2:
    features = st.multiselect(
        label="Select features", options=columns, default=columns[:2]
    )

with col3:
    aggregation = st.selectbox(
        label="Select aggregation method",
        options=["Mean", "Standard deviation"],
        disabled=(resolution == "Minutely"),
    )

if resolution == "Hourly":
    # f string needed to avoid python misinterpreting '%d'
    query = f"SELECT COUNT(DISTINCT strftime('%Y-%m-%d %H', time)) AS unique_hour_count FROM solar{''};"
    total_rows = conn.query(query, ttl=60).squeeze()
else:
    total_rows = conn.query("SELECT COUNT(*) FROM solar", ttl=60).squeeze()

win = {"Minutely": 24 * 60, "Hourly": 24}

min_val = 0
max_val = total_rows - win[resolution] - (1 if resolution == "Hourly" else 0)

s = st.slider(
    " ",
    min_val,
    max_val,
    value=max_val,
    step=1,
    label_visibility="hidden",
)

if resolution == "Hourly":
    if aggregation == "Mean":
        cols_to_query = []
        for col in features:
            cols_to_query.append(f", avg({col}) AS {col.lower()}")
        cols_to_query = "".join(cols_to_query)

    elif aggregation == "Standard deviation":
        cols_to_query = []
        for col in features:
            cols_to_query.append(
                f", sqrt(avg({col}*{col}) - avg({col})*avg({col})) AS {col.lower()}"
            )
        cols_to_query = "".join(cols_to_query)

    data_query = (
        f"SELECT "
        f"strftime('%Y-%m-%d %H:00:00', time) AS hourly_bucket"
        f"{cols_to_query}"
        f" FROM solar "
        f"GROUP BY hourly_bucket "
        f"ORDER BY hourly_bucket ASC "
        f"LIMIT {win[resolution]} "
        f"OFFSET {s};"
    )
    time_col = "hourly_bucket"
else:
    cols_to_query = ", ".join(["time"] + features)
    data_query = (
        f"SELECT {cols_to_query} FROM solar LIMIT {win[resolution]} OFFSET {s};"
    )
    time_col = "time"

plot_data = conn.query(data_query, ttl=60)

c1, c2 = st.columns(2)

with c1:
    start_str = datetime.fromisoformat(plot_data[time_col].iloc[0]).strftime(
        "%b %d, %H:%M"
    )
    end_str = datetime.fromisoformat(plot_data[time_col].iloc[-1]).strftime(
        "%b %d, %H:%M"
    )

    st.markdown(
        f"<div style='text-align: left;'>"
        f"Displaying data from {start_str} to {end_str}</div>",
        unsafe_allow_html=True,
    )

with c2:
    last_val = conn.query(
        "SELECT time FROM solar ORDER BY time DESC LIMIT 1", ttl=60
    ).squeeze()
    last_ts = datetime.fromisoformat(last_val).strftime("%b %d, %H:%M")

    st.markdown(
        f"<div style='text-align: right;'>" f"Data last updated at {last_ts}" f"</div>",
        unsafe_allow_html=True,
    )

label = {
    "Density": "Particle density (p/cm3)",
    "Speed": "Solar wind speed (km/s)",
    "Temperature": "Solar wind temperature (K)",
    "Pressure": "Solar wind dynamic pressure (nPa)",
    "Bz": "IMF Z-component (nT)",
    "Bt": "IMF magnitude (nT)",
}

for feature in features:

    st.markdown(
        (
            f"<div style='text-align: center;'>"
            f"<h3>Solar Wind {feature}</h3>"
            f"</div>"
        ),
        unsafe_allow_html=True,
    )

    chart = (
        alt.Chart(plot_data)
        .mark_line(color="#ff0000")
        .encode(
            x=alt.X(
                f"{time_col}:T",  # Dynamic time column
                axis=alt.Axis(
                    labelAngle=0,
                    tickCount=6,
                    format="%H:%M",
                    title="Time",
                ),
            ),
            y=alt.Y(
                f"{feature.lower()}:Q",  # Dynamic Y feature
                title=label[str(feature)],  # Using your existing label dictionary
            ),
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

with st.expander("More information on Solar Wind"):
    st.markdown(
        """
        The solar wind is a continuous stream of charged particles
        (plasma) emmited by the Sun's atmosphere. When this stream
        of particles reaches Earth, it transfers energy into the Earth's
        magnetosphere. Solar wind is made up of two components: the
        properties of the plasma (e.g. speed and density), and the
        properties of the embedded magnetic field, which is
        called the Interplanetary Magnetic Field (IMF). Geomganetic
        storms are typically triggered due to high speed solar wind
        combined with a strong IMF in the southward direction
        (Z-component). Storm intensity increases as the Bz value
        becomes more negative.
    """
    )
