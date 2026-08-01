import streamlit as st
import altair as alt
from app_utils import (
    data_last_synced,
    init_db,
    get_latest_timestamp,
    cached_query,
    github_link,
)

conn = init_db()

st.title("Solar Activity ☀️")

# services.swpc.noaa.gov's image feed sits behind an AWS WAF challenge that
# blocks non-browser clients - and since these load as <img> sub-resources
# (not full page navigations), even real browsers can't solve that challenge
# for them. NASA SDO publishes pre-rendered rolling animations (updated
# continuously, no on-demand render wait like Helioviewer's queueMovie,
# which takes minutes) with no such block. 512px keeps the total payload
# to ~21MB across all three instead of ~130MB at full 1024px resolution.
SDO_ANIMATION_URLS = {
    "Sunspots (Visible/HMI)": "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_512_HMIIC.mp4",
    "Solar Eruptions (Red/304Å)": "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_512_0304.mp4",
    "Solar Flares (Teal/131Å)": "https://sdo.gsfc.nasa.gov/assets/img/latest/mpeg/latest_512_0131.mp4",
}

# Animations are ~21MB total; stills are ~0.6MB. Default to stills and let
# users opt into the heavier animated view.
SDO_STILL_URLS = {
    "Sunspots (Visible/HMI)": "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_HMIIC.jpg",
    "Solar Eruptions (Red/304Å)": "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_0304.jpg",
    "Solar Flares (Teal/131Å)": "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_0131.jpg",
}


IMAGE_META = [
    {
        "key": "Sunspots (Visible/HMI)",
        "badge": "SDO / HMI",
        "color": "#e05d0b",
        "subtitle": "Continuum · Visible Light",
        "description": "Active regions and sunspots on the photosphere",
    },
    {
        "key": "Solar Eruptions (Red/304Å)",
        "badge": "GOES SUVI · 304Å",
        "color": "#f82f0c",
        "subtitle": "He II · Chromosphere / Transition Region",
        "description": "Filaments, prominences and coronal holes (75 MK)",
    },
    {
        "key": "Solar Flares (Teal/131Å)",
        "badge": "GOES SUVI · 131Å",
        "color": "#2dd4bf",
        "subtitle": "Fe VIII/XXI · Flare Plasma",
        "description": "High-energy flare and eruptive plasma (10 MK)",
    },
]


@st.fragment(run_every=300)
def solar_images_section():
    header_col, toggle_col = st.columns([3, 1])
    with header_col:
        st.subheader("Latest Solar View")
    with toggle_col:
        show_animations = st.toggle(
            "Animate (~21MB)", value=False, key="show_solar_animations"
        )

    cols = st.columns(3)
    for col, meta in zip(cols, IMAGE_META):
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
            if show_animations:
                st.markdown(
                    f"""<video autoplay loop muted playsinline
                        style="width:100%; aspect-ratio:1/1; border-radius:8px; display:block;">
                        <source src="{SDO_ANIMATION_URLS[meta['key']]}" type="video/mp4">
                    </video>""",
                    unsafe_allow_html=True,
                )
            else:
                st.image(SDO_STILL_URLS[meta["key"]], width="stretch")


@st.fragment
def sunspot_plot_section():
    latest_ts = get_latest_timestamp(conn, "ssn")

    cl1, cl2, cl3 = st.columns([1, 1, 1])
    with cl1:
        ssn_range = st.radio(
            "Time range",
            options=["Last Month", "Last Year", "Last Full Cycle"],
            index=2,
            horizontal=True,
            label_visibility="collapsed",
        )

    if ssn_range == "Last Month":
        query = "SELECT time, swpc_ssn FROM ssn WHERE time >= (SELECT MAX(time) FROM ssn) - INTERVAL '1 month' ORDER BY time ASC"
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
                    title="Date",
                ),
            ),
            y=alt.Y("swpc_ssn:Q", title="Sunspot Count"),
        )
        .properties(height=400)
    )

    st.altair_chart(chart, width="stretch")

    with st.expander("More information on Solar Activity", expanded=True):
        st.markdown("""
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
        """)


solar_images_section()
st.markdown("<br>", unsafe_allow_html=True)
sunspot_plot_section()
github_link()
