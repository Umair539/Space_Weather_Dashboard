import streamlit as st
import altair as alt
from app_utils import data_last_synced, init_db, get_latest_timestamp, cached_query

conn = init_db()

PARAM_COLORS = {
    "Speed": "#00bcd4",
    "Density": "#69db7c",
    "Temperature": "#f4c430",
    "Bz": "#c084fc",
    "Bx": "#60a5fa",
    "By": "#2dd4bf",
    "Bt": "#fbbf24",
    "Pressure": "#fb923c",
}

st.title("Solar Wind Properties 🛰️")


@st.fragment(run_every=120)
def solar_wind_section():
    latest_ts = get_latest_timestamp(conn, "solar")

    col1, col2 = st.columns(2)

    with col1:
        resolution = st.selectbox(
            label="Select time resolution", options=["Minutely", "Hourly"], index=0
        )

    df = cached_query(conn, "SELECT * FROM solar LIMIT 0", latest_ts)
    columns = [c.capitalize() for c in df.columns][1:]

    with col2:
        features = st.multiselect(
            label="Select features", options=columns, default=["Speed", "Bz"]
        )

    cl1, cl2 = st.columns([1, 1])
    with cl1:
        time_range = st.radio(
            "Time range",
            options=["Last 24 Hours", "Last Week", "Last Month"],
            horizontal=True,
            label_visibility="collapsed",
        )

    intervals = {
        "Last 24 Hours": "24 hours",
        "Last Week": "7 days",
        "Last Month": "31 days",
    }
    interval = intervals[time_range]

    if resolution == "Hourly":
        cols_agg = "".join(
            f", round(avg({col})::numeric, 2) AS {col.lower()}" for col in features
        )
        data_query = (
            f"SELECT date_trunc('hour', time) AS hourly_bucket"
            f"{cols_agg}"
            f" FROM solar"
            f" WHERE time >= (SELECT MAX(time) FROM solar) - INTERVAL '{interval}'"
            f" GROUP BY hourly_bucket"
            f" HAVING COUNT(*) = 60"
            f" ORDER BY hourly_bucket ASC;"
        )
        time_col = "hourly_bucket"
    else:
        cols_str = ", ".join(["time"] + features)
        data_query = (
            f"SELECT {cols_str}"
            f" FROM solar"
            f" WHERE time >= (SELECT MAX(time) FROM solar) - INTERVAL '{interval}'"
            f" ORDER BY time ASC;"
        )
        time_col = "time"

    plot_data = cached_query(conn, data_query, latest_ts)

    start_str = plot_data[time_col].iloc[0].strftime("%b %d, %H:%M")
    end_str = plot_data[time_col].iloc[-1].strftime("%b %d, %H:%M")
    with cl2:
        st.markdown(
            f"<div style='text-align:right;'>Displaying data from {start_str} to {end_str}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='text-align:right; font-style:italic; color:gray;'>{data_last_synced(conn)}</div>",
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
            f"<div style='text-align: center;'><h3>Solar Wind {feature}</h3></div>",
            unsafe_allow_html=True,
        )

        chart = (
            alt.Chart(plot_data)
            .mark_line(color=PARAM_COLORS.get(feature, "#00bcd4"))
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


solar_wind_section()
