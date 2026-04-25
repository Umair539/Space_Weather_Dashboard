import streamlit as st
import altair as alt
from app_utils import data_last_synced, init_db, get_latest_timestamp, cached_query

conn = init_db()

st.title("Solar Activity ☀️")


@st.fragment(run_every=120)
def sun_section():
    latest_ts = get_latest_timestamp(conn, "ssn")

    st.subheader("Latest Solar View")

    solar_flavors = {
        "Sunspots (Visible/HMI)": "https://services.swpc.noaa.gov/images/animations/sdo-hmii/latest.jpg",
        "Solar Eruptions (Red/304Å)": "https://services.swpc.noaa.gov/images/animations/suvi/primary/304/latest.png",
        "Solar Flares (Teal/131Å)": "https://services.swpc.noaa.gov/images/animations/suvi/primary/131/latest.png",
    }

    image_meta = [
        {
            "key": "Sunspots (Visible/HMI)",
            "badge": "SDO / HMI",
            "color": "#00bcd4",
            "subtitle": "Continuum · Visible Light",
            "description": "Active regions and sunspots on the photosphere",
        },
        {
            "key": "Solar Eruptions (Red/304Å)",
            "badge": "GOES SUVI · 304Å",
            "color": "#e05d0b",
            "subtitle": "He II · Chromosphere / Transition Region",
            "description": "Filaments, prominences and coronal holes (75,000 K)",
        },
        {
            "key": "Solar Flares (Teal/131Å)",
            "badge": "GOES SUVI · 131Å",
            "color": "#2dd4bf",
            "subtitle": "Fe VIII/XXI · Flare Plasma",
            "description": "High-energy flare and eruptive plasma (10 MK)",
        },
    ]

    cols = st.columns(3)
    for col, meta in zip(cols, image_meta):
        with col:
            st.markdown(
                f"""<div style="border:1px solid {meta['color']}55; border-radius:8px; padding:12px 14px; margin-bottom:8px;">
                    <span style="border:1px solid {meta['color']}; color:{meta['color']}; border-radius:4px;
                        padding:3px 10px; font-weight:700; letter-spacing:1px;">{meta['badge']}</span>
                    <div style="color:#c9d1d9; margin-top:8px;">{meta['subtitle']}</div>
                    <div style="color:{meta['color']}cc; font-style:italic; margin-top:4px;">{meta['description']}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.image(solar_flavors[meta["key"]], width="stretch")

    st.markdown("<br>", unsafe_allow_html=True)

    cl1, cl2, cl3 = st.columns([1, 2, 1])
    with cl1:
        ssn_range = st.radio(
            "Time range",
            options=["Last Month", "Last Year", "Last Full Cycle"],
            horizontal=True,
            label_visibility="collapsed",
        )

    if ssn_range == "Last Month":
        query = "SELECT time, swpc_ssn FROM ssn WHERE time >= (SELECT MAX(time) FROM ssn) - INTERVAL '31 days' ORDER BY time ASC"
        fmt = "%b %d %Y"
    elif ssn_range == "Last Year":
        query = "SELECT time, swpc_ssn FROM ssn WHERE time >= (SELECT MAX(time) FROM ssn) - INTERVAL '1 year' ORDER BY time ASC"
        fmt = "%b %Y"
    else:
        query = """
        SELECT DATE_TRUNC('month', time) AS time, AVG(swpc_ssn) AS swpc_ssn
        FROM ssn
        GROUP BY DATE_TRUNC('month', time)
        ORDER BY time ASC
        """
        fmt = "%Y"

    plot_data = cached_query(conn, query, latest_ts)

    start_str = plot_data["time"].iloc[0].strftime("%b %d %Y")
    end_str = plot_data["time"].iloc[-1].strftime("%b %d %Y")
    with cl2:
        st.markdown(
            "<div style='text-align:center;'><h3>Sunspots</h3></div>",
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
