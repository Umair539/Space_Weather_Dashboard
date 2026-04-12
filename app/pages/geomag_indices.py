import streamlit as st
import altair as alt
from streamlit_autorefresh import st_autorefresh
from app_utils import safe_query, data_last_synced, init_db, is_data_fresh

conn = init_db()
synced = is_data_fresh(conn)

st.title("Real Time Geomgagnetic Indices 📡")

if not is_data_fresh(conn):
    st.info("Syncing latest space weather data...")

data_range = safe_query(conn, "SELECT time FROM dst;")
options = data_range.iloc[:, 0].tolist()
options = options[:-24]
s_dst = st.select_slider(
    "Select start date",
    options=options,
    value=options[-1],
    format_func=lambda x: x.strftime("%b %d, %H:%M"),
)
query = f"""
    SELECT p.time, d.dst, p.dst_predictions
    FROM dst_predictions p
    LEFT JOIN dst d ON p.time = d.time
    WHERE p.time >= '{s_dst}'
    ORDER BY p.time ASC
    LIMIT 25
    """
plot_data = safe_query(conn, query)

c1, c2 = st.columns(2)

with c1:
    start_str = plot_data["time"].iloc[0].strftime("%b %d, %H:%M")
    end_str = plot_data["time"].iloc[-1].strftime("%b %d, %H:%M")

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

st.markdown(
    "<div style='text-align: center;'><h3>Dst index</h3></div>",
    unsafe_allow_html=True,
)

chart = (
    alt.Chart(plot_data)
    .transform_fold(
        ["dst", "dst_predictions"],
        as_=["Series", "Value"],
    )
    .mark_line()
    .encode(
        x=alt.X(
            "time:T",
            axis=alt.Axis(
                labelAngle=0,
                tickCount=6,
                format="%b %d, %H:%M",
                title="Time",
            ),
        ),
        y=alt.Y("Value:Q", title="Dst (nT)"),
        color=alt.Color(
            "Series:N",
            scale=alt.Scale(range=["#ff0000", "#a9a9a9"]),
            legend=alt.Legend(
                orient="none",
                legendX=5,  # pixels from the left
                legendY=5,  # pixels from the top
                direction="vertical",  # vertical stack
                title=None,
                padding=5,
                labelExpr="datum.label == 'dst' ? 'Observed Dst' : datum.label == 'dst_predictions' ? 'Model Prediction' : datum.label",
            ),
        ),
    )
    .properties(height=400)
)

st.altair_chart(chart, width="stretch")

with st.expander("More information on Dst index", expanded=True):
    st.markdown(
        """
        The Disturbance Storm Time (Dst) index is a measure of geomagnetic
        activity used to assess the severity of geomagnetic storms. It is
        expressed in nanoTeslas and is based on the average value of the
        horizontal component of the Earth's magnetic field measured at four
        near-equatorial geomagnetic observatories at hourly intervals. It
        measures the growth and recovery of the ring current in the Earth's
        magnetosphere. The lower these values get, the more energy is stored
        in Earth's magnetosphere. If the Dst index drops below -50 nT, this
        indicates a moderate storm is taking place, and below -100 nT
        indicates a severe storm taking place. The chart compares these
        observed measurements with the corresponding predicted values.
    """
    )

data_range = safe_query(conn, "SELECT time FROM kp;")
options = data_range.iloc[:, 0].tolist()
options = options[:-24]
ss_kp = st.select_slider(
    "Select start date",
    options=options,
    value=options[-1],
    format_func=lambda x: x.strftime("%b %d, %H:%M"),
)
query_kp = f"""SELECT time, kp."Kp" FROM kp WHERE time >= '{ss_kp}' LIMIT 25"""
plot_data_kp = safe_query(conn, query_kp)

start_str_kp = plot_data_kp["time"].iloc[0].strftime("%b %d, %H:%M")
end_str_kp = plot_data_kp["time"].iloc[-1].strftime("%b %d, %H:%M")

st.markdown(
    f"Displaying data from {start_str_kp} to {end_str_kp}</p></div>",
    unsafe_allow_html=True,
)

st.markdown(
    "<div style='text-align: center;'><h3>Kp Index</h3></div>",
    unsafe_allow_html=True,
)

chart_kp = (
    alt.Chart(plot_data_kp)
    .mark_line(color="#ff0000")
    .encode(
        x=alt.X(
            "time:T",
            axis=alt.Axis(
                labelAngle=0,
                tickCount=6,
                format="%b %d, %H:%M",
                title="Time",
            ),
        ),
        y=alt.Y("Kp:Q", title="Kp Index", scale=alt.Scale(domain=[0, 9])),
    )
    .properties(height=400)
)

st.altair_chart(chart_kp, width="stretch")

with st.expander("More information on Kp index", expanded=True):
    st.markdown(
        """
        The Kp-index is a geomagnetic activity index based on data from
        magnetometers around the world measured every 3 hours. The graph
        above displays the observed Kp-value from the Planetary K-index
        of the NOAA SWPC and can be used to make a rough estimate of the
        current global geomagnetic conditions. It is a quasi-logarithmic
        index from 0 to 9 where a value of 5 indicates that a moderate storm is
        occuring, a value of 7 indicate a severe storm is occuring, and
        a value of 9 indicates an extreme storm is occuring.
    """
    )

if synced:
    st_autorefresh(60000)
else:
    st_autorefresh(5000)
