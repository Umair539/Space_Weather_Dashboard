import streamlit as st
import altair as alt
from streamlit_autorefresh import st_autorefresh
from app_utils import safe_query, data_last_synced, init_db, is_data_fresh

conn = init_db()
synced = is_data_fresh(conn)

st.title("Real Time Solar Activity ☀️")

c1, c2 = st.columns([3, 1], vertical_alignment="bottom")

with c1:
    st.subheader("Live Solar View")

with c2:
    # Use a div to keep the text right-aligned within its column
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


data_range = safe_query(conn, "SELECT time FROM ssn ORDER BY time ASC;")
options = data_range.iloc[:, 0].tolist()
options = options[:-30]
s_ssn = st.select_slider(
    "Select start date",
    options=options,
    value=options[-1],
    format_func=lambda x: x.strftime("%b %d %Y"),
)
query = (
    f"SELECT time, swpc_ssn FROM ssn WHERE time >= '{s_ssn}' ORDER BY time ASC LIMIT 31"
)
plot_data = safe_query(conn, query)

c1, c2 = st.columns(2)


start_str = plot_data["time"].iloc[0].strftime("%b %d")
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
                format="%b %d",
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


if synced:
    st_autorefresh(60000)
else:
    st_autorefresh(5000)
