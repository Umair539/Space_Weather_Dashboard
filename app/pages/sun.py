import streamlit as st
import altair as alt
from app_utils import data_last_synced, init_db, get_latest_timestamp, cached_query

conn = init_db()

st.title("Solar Activity ☀️")


@st.fragment(run_every=120)
def sun_section():
    latest_ts = get_latest_timestamp(conn, "ssn")

    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")

    with c1:
        st.subheader("Latest Solar View")

    with c2:
        st.markdown(
            f"<div style='text-align: right; font-style: italic; color: gray;'>"
            f"{data_last_synced(conn)}"
            f"</div>",
            unsafe_allow_html=True,
        )

    solar_flavors = {
        "Sunspots (Visible/HMI)": "https://services.swpc.noaa.gov/images/animations/sdo-hmii/latest.jpg",
        "Solar Eruptions (Red/304Å)": "https://services.swpc.noaa.gov/images/animations/suvi/primary/304/latest.png",
        "Solar Flares (Teal/131Å)": "https://services.swpc.noaa.gov/images/animations/suvi/primary/131/latest.png",
    }

    col1, col2, col3 = st.columns(3)

    with col1:
        st.image(solar_flavors["Sunspots (Visible/HMI)"], caption="Sunspots (HMI)")
    with col2:
        st.image(solar_flavors["Solar Eruptions (Red/304Å)"], caption="Eruptions (304Å)")
    with col3:
        st.image(solar_flavors["Solar Flares (Teal/131Å)"], caption="Flares (131Å)")

    ssn_range = st.radio(
        "Time range",
        options=["Last Month", "Last Year", "Last Full Cycle"],
        horizontal=True,
    )

    if ssn_range == "Last Month":
        query = "SELECT time, swpc_ssn FROM ssn WHERE time >= (SELECT MAX(time) FROM ssn) - INTERVAL '31 days' ORDER BY time ASC"
        fmt = "%b %d %Y"
    elif ssn_range == "Last Year":
        query = "SELECT time, swpc_ssn FROM ssn WHERE time >= (SELECT MAX(time) FROM ssn) - INTERVAL '1 year' ORDER BY time ASC"
        fmt = "%b %Y"
    else:
        query = "SELECT time, swpc_ssn FROM ssn ORDER BY time ASC"
        fmt = "%Y"

    plot_data = cached_query(conn, query, latest_ts)

    start_str = plot_data["time"].iloc[0].strftime("%b %d %Y")
    end_str = plot_data["time"].iloc[-1].strftime("%b %d %Y")

    st.markdown(
        f"<div style='text-align: left;'>"
        f"Displaying data from {start_str} to {end_str}</div>",
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
                    format=fmt,
                    title="Time",
                ),
            ),
            y=alt.Y("swpc_ssn:Q", title="Sunspot Count"),
        )
        .properties(height=400)
    )

    st.altair_chart(chart, width="stretch")

    with st.expander("More information on Solar Activity", expanded=True):
        st.markdown(
            """
            The Sun follows a periodic 11-year cycle of activity driven by its
            internal magnetic field, which completely flips its orientation once
            per decade. This progression is most visibly tracked by the number
            of sunspots, which are dark, cooler regions of intense magnetic activity
            on the surface of the sun that indicate how active the Sun is. During solar
            minimum, very few sunspots are observed, whereas solar maximum brings
            a high concentration of spots, often leading to more frequent solar
            flares. These cycles are closely linked to the solar wind, as a more
            active Sun releases a more turbulent stream of particles that can
            impact Earth's magnetic field. The chart displays these counts to show
            where the current solar activity falls within the broader 11-year cycle.
        """
        )


sun_section()
