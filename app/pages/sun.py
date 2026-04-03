import streamlit as st
import altair as alt
from streamlit_autorefresh import st_autorefresh
from utils import safe_query, data_last_synced, init_db

init_db()
conn = st.session_state.neon_db

st.title("Real Time Solar Activity ☀️")

data_range = safe_query(conn, "SELECT TO_CHAR(time, 'YYYY-MM-DD') FROM ssn;")
s_ssn = st.select_slider("Select start date", data_range[:-3])
query = f"SELECT time, swpc_ssn FROM ssn WHERE time >= '{s_ssn}'LIMIT 31"
plot_data = safe_query(conn, query)

c1, c2 = st.columns(2)

with c1:
    start_str = plot_data["time"].iloc[0].strftime("%b %d")
    end_str = plot_data["time"].iloc[-1].strftime("%b %d")

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

st.markdown(
    "<div style='text-align: center;'><h3>Sunspots</h3></div>",
    unsafe_allow_html=True,
)

chart = (
    alt.Chart(plot_data)
    .mark_line(color="#ff0000")
    .encode(
        x=alt.X(
            "time:T",
            axis=alt.Axis(
                labelAngle=0,
                tickCount=6,
                format="%b %d",
                title="Time",
            ),
        ),
        y=alt.Y("swpc_ssn:Q", title="Sunspot Count"),
    )
    .properties(height=400)
)

st.altair_chart(chart, width="stretch")

with st.expander("More information on Solar Activity"):
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

st_autorefresh(60000)
