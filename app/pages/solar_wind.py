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

win = {"Minutely": 24 * 60, "Hourly": 24}

if resolution == "Hourly":
    query = f"SELECT COUNT(DISTINCT strftime('%Y-%m-%d %H', time)) AS unique_hour_count FROM solar;"
    total_rows = conn.query(query, ttl=60).squeeze()
else:
    total_rows = conn.query("SELECT COUNT(*) FROM solar", ttl=60).squeeze()

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
    cols_to_query = []
    for col in features:
        cols_to_query.append(f", avg({col}) AS {col.lower()}")
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
    x_axis = "hourly_bucket"
else:
    cols_to_query = ", ".join(["time"] + features)
    data_query = (
        f"SELECT {cols_to_query} FROM solar LIMIT {win[resolution]} OFFSET {s};"
    )
    x_axis = "time"

c1, c2 = st.columns(2)

# with c1:
#     st.markdown(
#         (
#             f"<div style='text-align: left;'>"
#             f"Displaying data from {df['time'][s]} "
#             f"to {df['time'][s + win[resolution] - 1]}"
#             f"</div>"
#         ),
#         unsafe_allow_html=True,
#     )

# with c2:
#     st.markdown(
#         (
#             f"<div style='text-align: right;'>"
#             f"Data last updated at {solar['time'].iloc[-1]}"
#             f"</div>"
#         ),
#         unsafe_allow_html=True,
#     )

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

    st.line_chart(
        data=conn.query(data_query, ttl=60),
        x=x_axis,
        y=str(feature.lower()),
        x_label="Time",
        y_label=label[str(feature)],
        color="#ff0000",
    )

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
