import streamlit as st
import altair as alt
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

st_autorefresh(60000)
conn = st.session_state.noaa_data_db

st.title("Real Time Geomgagnetic Indices 📡")

total_rows = conn.query("SELECT COUNT(*) FROM dst", ttl=60).squeeze() - 24

s_dst = st.slider(
    " ",
    0,
    total_rows,
    value=total_rows,
    step=1,
    label_visibility="hidden",
)

query = f"SELECT * FROM dst LIMIT 24 OFFSET {s_dst}"
plot_data = conn.query(query, ttl=60)

c1, c2 = st.columns(2)

with c1:
    start_str = datetime.fromisoformat(plot_data["time"].iloc[0]).strftime(
        "%b %d, %H:%M"
    )
    end_str = datetime.fromisoformat(plot_data["time"].iloc[-1]).strftime(
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

st.markdown(
    "<div style='text-align: center;'><h3>Dst index</h3></div>",
    unsafe_allow_html=True,
)

chart = (
    alt.Chart(plot_data)
    .mark_line(color="#ff0000")
    .encode(
        x=alt.X(
            "time:T",
            axis=alt.Axis(
                labelAngle=0,  # Forces labels to stay horizontal
                tickCount=6,  # Reduces number of labels to avoid overlap
                format="%H:%M",  # Makes labels shorter (just HH:MM)
                title="Time",
            ),
        ),
        y=alt.Y("dst:Q", title="Dst (nT)"),  # Keeps your Y-axis as it was
    )
    .properties(height=400)
)

st.altair_chart(chart, use_container_width=True)

with st.expander("More information on Dst index"):
    st.markdown(
        """
        The Disturbance Storm Time (Dst) index is a measure of geomagnetic
        activity used to assess the severity of geomagnetic storms. It is
        expressed in nanoTeslas and is based on the average value of the
        horizontal component of the Earth's magnetic field measured at four
        near-equatorial geomagnetic observatories at hourly intervals. It
        measures the growth and recovery of the ring current in the Earth's
        magnetosphere. The lower these values get, the more energy is stored
        in Earth's magnetosphere.If the Dst index drops below -50 nT, this
        indicates a moderate storm is taking place, and below -100 nT
        indicates a severe storm taking place.
    """
    )

total_rows_kp = conn.query("SELECT COUNT(*) FROM kp", ttl=60).squeeze() - 8

s_kp = st.slider(
    "  ",  # Unique key for Kp slider
    0,
    total_rows_kp,
    value=total_rows_kp,
    step=1,
    label_visibility="hidden",
    key="kp_slider",  # Important: Slider keys must be unique if you have two on one page
)

# 2. Query the 8-row window for Kp
query_kp = f"SELECT * FROM kp LIMIT 8 OFFSET {s_kp}"
plot_data_kp = conn.query(query_kp, ttl=60)

# 3. Display time window for Kp
start_str_kp = datetime.fromisoformat(plot_data_kp["time"].iloc[0]).strftime(
    "%b %d, %H:%M"
)
end_str_kp = datetime.fromisoformat(plot_data_kp["time"].iloc[-1]).strftime(
    "%b %d, %H:%M"
)

st.markdown(
    f"<div style='text-align: left;'><h3>Kp index</h3>"
    f"Displaying data from {start_str_kp} to {end_str_kp}</p></div>",
    unsafe_allow_html=True,
)

# 4. Altair Chart for Kp
chart_kp = (
    alt.Chart(plot_data_kp)
    .mark_line(color="#ff0000")
    .encode(
        x=alt.X(
            "time:T",
            axis=alt.Axis(
                labelAngle=0,
                tickCount=4,  # Kp has fewer points, so 4 ticks is plenty
                format="%H:%M",
                title="Time",
            ),
        ),
        y=alt.Y(
            "Kp:Q", title="Kp Index", scale=alt.Scale(domain=[0, 9])
        ),  # Kp is always 0-9
    )
    .properties(height=300)
)

st.altair_chart(chart_kp, use_container_width=True)

with st.expander("More information on Kp index"):
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
