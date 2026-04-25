import streamlit as st
import altair as alt
import pandas as pd
from app_utils import data_last_synced, init_db, get_latest_timestamp, cached_query

conn = init_db()

st.title("Geomgagnetic Indices 📡")

intervals = {
    "Last 24 Hours": "24 hours",
    "Last Week": "7 days",
    "Last Month": "31 days",
}


@st.fragment(run_every=120)
def dst_section():
    latest_ts = get_latest_timestamp(conn, "dst_predictions")

    cl1, cl2, cl3 = st.columns([1, 2, 1])
    with cl1:
        dst_range = st.radio(
            "Dst time range",
            options=list(intervals.keys()),
            horizontal=True,
            key="dst_range",
            label_visibility="collapsed",
        )

    dst_interval = intervals[dst_range]

    dst_query = f"""
        SELECT p.time, d.dst, p.dst_predictions
        FROM dst_predictions p
        INNER JOIN dst d ON p.time = d.time
        WHERE p.time >= (SELECT MAX(time) FROM dst_predictions) - INTERVAL '{dst_interval}'
        ORDER BY p.time ASC
    """
    plot_data = cached_query(conn, dst_query, latest_ts)

    start_str = plot_data["time"].iloc[0].strftime("%b %d, %H:%M")
    end_str = plot_data["time"].iloc[-1].strftime("%b %d, %H:%M")
    with cl2:
        st.markdown(
            "<div style='text-align:center;'><h3>Dst Index</h3></div>",
            unsafe_allow_html=True,
        )
    with cl3:
        st.markdown(
            f"<div style='text-align:right;'>Displaying data from {start_str} to {end_str}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='text-align:right; font-style:italic; color:gray;'>{data_last_synced(conn)}</div>",
            unsafe_allow_html=True,
        )

    dst_vals = pd.concat([plot_data["dst"], plot_data["dst_predictions"]]).dropna()
    y_min_dst = float(dst_vals.min()) - 5
    y_max_dst = float(dst_vals.max()) + 5

    chart = (
        alt.Chart(plot_data)
        .transform_fold(["dst", "dst_predictions"], as_=["Series", "Value"])
        .mark_line()
        .encode(
            x=alt.X(
                "time:T",
                axis=alt.Axis(
                    labelAngle=0, tickCount=6, format="%b %d, %H:%M", title="Time"
                ),
            ),
            y=alt.Y(
                "Value:Q",
                title="Dst (nT)",
                scale=alt.Scale(domain=[y_min_dst, y_max_dst]),
            ),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(range=["#ff0000", "#ffffff"]),
                legend=alt.Legend(
                    orient="none",
                    legendX=5,
                    legendY=5,
                    direction="vertical",
                    title=None,
                    padding=5,
                    labelExpr="datum.label == 'dst' ? 'Observed Dst' : 'Model Prediction'",
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


@st.fragment(run_every=120)
def kp_section():
    latest_ts = get_latest_timestamp(conn, "kp")

    cl1, cl2, cl3 = st.columns([1, 2, 1])
    with cl1:
        kp_range = st.radio(
            "Kp time range",
            options=list(intervals.keys()),
            horizontal=True,
            key="kp_range",
            label_visibility="collapsed",
        )

    kp_interval = intervals[kp_range]

    query_kp = f"""
        SELECT time, kp."Kp"
        FROM kp
        WHERE time >= (SELECT MAX(time) FROM kp) - INTERVAL '{kp_interval}'
        ORDER BY time ASC
    """
    plot_data_kp = cached_query(conn, query_kp, latest_ts)

    start_str_kp = plot_data_kp["time"].iloc[0].strftime("%b %d, %H:%M")
    end_str_kp = plot_data_kp["time"].iloc[-1].strftime("%b %d, %H:%M")
    with cl2:
        st.markdown(
            "<div style='text-align:center;'><h3>Kp Index</h3></div>",
            unsafe_allow_html=True,
        )
    with cl3:
        st.markdown(
            f"<div style='text-align:right;'>Displaying data from {start_str_kp} to {end_str_kp}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='text-align:right; font-style:italic; color:gray;'>{data_last_synced(conn)}</div>",
            unsafe_allow_html=True,
        )

    chart_kp = (
        alt.Chart(plot_data_kp)
        .mark_line(color="#ff0000")
        .encode(
            x=alt.X(
                "time:T",
                axis=alt.Axis(
                    labelAngle=0, tickCount=6, format="%b %d, %H:%M", title="Time"
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


dst_section()
kp_section()
