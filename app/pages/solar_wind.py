import streamlit as st
import altair as alt
from streamlit_autorefresh import st_autorefresh
from utils import safe_query, data_last_synced, init_db, is_data_fresh

conn = init_db()
synced = is_data_fresh(conn)

st.title("Real Time Solar Wind Properties 🛰️")

col1, col2 = st.columns(2)

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

win = {"Minutely": 24 * 60, "Hourly": 24}

if resolution == "Hourly":
    data_range = safe_query(
        conn,
        """
        SELECT date_trunc('hour', time) AS hour
        FROM solar
        GROUP BY hour
        HAVING count(*) = 60
        ORDER BY hour ASC
        """,
    )
    options = data_range.iloc[:, 0].tolist()
    options = options[:-24]
    s = st.select_slider(
        "Select start date",
        options=options,
        value=options[-1],
        format_func=lambda x: x.strftime("%b %d, %H:%M"),
    )

    cols_to_query = []
    for col in features:
        cols_to_query.append(f", round(avg({col})::numeric, 2) AS {col.lower()}")

    cols_to_query = "".join(cols_to_query)

    data_query = (
        f"SELECT "
        f"date_trunc('hour', time) AS hourly_bucket"
        f"{cols_to_query}"
        f" FROM solar "
        f"WHERE date_trunc('hour', time) >= '{s}' "
        f"GROUP BY hourly_bucket "
        f"HAVING COUNT(*) = 60 "
        f"ORDER BY hourly_bucket ASC "
        f"LIMIT {win[resolution]};"
    )
    time_col = "hourly_bucket"

elif resolution == "Minutely":
    data_range = safe_query(conn, "SELECT time FROM solar ORDER BY time")
    options = data_range.iloc[:, 0].tolist()
    options = options[: -24 * 60 + 1]
    s = st.select_slider(
        "Select start date",
        options=options,
        value=options[-1],
        format_func=lambda x: x.strftime("%b %d, %H:%M"),
    )

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
    start_str = plot_data[time_col].iloc[0].strftime("%b %d, %H:%M")
    end_str = plot_data[time_col].iloc[-1].strftime("%b %d, %H:%M")

    st.markdown(
        f"<div style='text-align: left;'>"
        f"Displaying data from {start_str} to {end_str}</div>",
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"<div style='text-align: right; font-style: italic; color: gray;'>"
        f"{data_last_synced(conn)}"
        f"</div>",
        unsafe_allow_html=True,
    )

label = {
    "Density": "Particle density (p/cm3)",
    "Speed": "Solar wind speed (km/s)",
    "Temperature": "Solar wind temperature (K)",
    "Pressure": "Solar wind dynamic pressure (nPa)",
    "Bz": "IMF Z-component (nT)",
    "By": "IMF Y-component (nT)",
    "Bx": "IMF X-component (nT)",
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
                f"{time_col}:T",
                axis=alt.Axis(
                    labelAngle=0,
                    tickCount=6,
                    format="%b %d, %H:%M",
                    title="Time",
                ),
            ),
            y=alt.Y(
                f"{feature.lower()}:Q",
                title=label[str(feature)],
            ),
        )
        .properties(height=400)
    )

    st.altair_chart(chart, width="stretch")

with st.expander("More information on Solar Wind", expanded=True):
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

if synced:
    st_autorefresh(60000)
else:
    st_autorefresh(5000)
