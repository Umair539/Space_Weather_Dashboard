import streamlit as st
import altair as alt
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
from utils import safe_query, data_last_synced, init_db

init_db()
conn = st.session_state.neon_db

st.title("Real Time Solar Wind Properties 🛰️")

col1, col2, col3 = st.columns(3)

with col1:
    resolution = st.selectbox(
        label="Select time resolution", options=["Minutely", "Hourly"], index=0
    )

df = safe_query(conn, "SELECT * FROM solar LIMIT 0")
columns = [c.capitalize() for c in df.columns][1:]

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
    data_range = safe_query(
        conn,
        """
        SELECT substr(time, 1, 13) || ':00:00' AS hour
        FROM solar
        GROUP BY hour
        HAVING count(*) == 60
        ORDER BY hour ASC
        """,
    )
    s = st.select_slider("Select start date", data_range[:-24])

    cols_to_query = []
    for col in features:
        if aggregation == "Mean":
            cols_to_query.append(f", round(avg({col}), 2) AS {col.lower()}")

        elif aggregation == "Standard deviation":
            cols_to_query.append(
                f", round(sqrt(avg({col}*{col}) - avg({col})*avg({col})), 2) AS {col.lower()}"
            )
    cols_to_query = "".join(cols_to_query)

    data_query = (
        f"SELECT "
        f"substr(time, 1, 13) || ':00:00' AS hourly_bucket"
        f"{cols_to_query}"
        f" FROM solar "
        f"WHERE hourly_bucket >= '{s}' "
        f"GROUP BY hourly_bucket "
        f"HAVING count(*) = 60 "  # full 60 minute buckets
        f"ORDER BY hourly_bucket ASC "
        f"LIMIT {win[resolution]}; "
    )
    time_col = "hourly_bucket"

elif resolution == "Minutely":
    data_range = safe_query(conn, "SELECT substr(time, 1, 16) from solar")
    s = st.select_slider("Select start date", data_range[: -24 * 60 + 1])

    cols_to_query = ", ".join(["time"] + features)
    data_query = (
        f"SELECT {cols_to_query} "
        f"FROM solar "
        f"WHERE time >= '{s}' "
        f"LIMIT {win[resolution]};"
    )
    time_col = "time"

plot_data = safe_query(conn, data_query)

c1, c2 = st.columns(2)

with c1:
    start_str = datetime.fromisoformat(plot_data[time_col].iloc[0])
    end_str = datetime.fromisoformat(plot_data[time_col].iloc[-1])

    st.markdown(
        f"<div style='text-align: left;'>"
        f"Displaying data from {start_str} to {end_str}</div>",
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"<div style='text-align: right; font-style: italic; color: gray;'>"
        f"Data last synced at {data_last_synced()}"
        f"</div>",
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

    st.altair_chart(chart, width="stretch")

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

st_autorefresh(60000)
