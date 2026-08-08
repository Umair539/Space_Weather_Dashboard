import streamlit as st
import altair as alt
from app_utils import (
    api_dataframe,
    data_last_synced,
    github_link,
)

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

# Plottable solar wind measurements. Listed explicitly (rather than
# introspected via "SELECT *") so non-feature columns in the "solar" table -
# e.g. "time" and "updated_at" (added for cache-invalidation purposes) -
# never leak into the "Select features" multiselect.
FEATURE_COLUMNS = ["density", "speed", "temperature", "bz", "bx", "by", "bt", "pressure"]

st.title("Solar Wind Properties 🛰️")


@st.fragment(run_every=120)
def solar_wind_section():
    columns = [c.capitalize() for c in FEATURE_COLUMNS]

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

    # "Last Month" is served pre-aggregated to hourly means by the API (the
    # same complete-hours-only rule the old HAVING COUNT(*) = 60 enforced),
    # so both branches now differ only by endpoint - and both label the
    # timestamp column "time", unlike the old "hourly_bucket" alias.
    params = {"columns": [f.lower() for f in features]}
    if time_range == "Last Month":
        plot_data = api_dataframe("/solar-wind/monthly", params)
    else:
        params["interval"] = {"Last 24 Hours": "24h", "Last Week": "7d"}[time_range]
        plot_data = api_dataframe("/solar-wind/raw", params)

    start_str = plot_data["time"].iloc[0].strftime("%b %d, %H:%M")
    end_str = plot_data["time"].iloc[-1].strftime("%b %d, %H:%M")
    with cl2:
        st.markdown(
            f"<div style='text-align:right;'>Displaying data from {start_str} to {end_str}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='text-align:right; font-style:italic; color:gray;'>{data_last_synced()}</div>",
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
                    "time:T",
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
        st.markdown("""
            The solar wind is a continuous stream of charged particles
            (plasma) emitted by the Sun's atmosphere. When this stream
            of particles reaches Earth, it transfers energy into the Earth's
            magnetosphere. Solar wind is made up of two components: the
            properties of the plasma (e.g. speed and density), and the
            properties of the embedded magnetic field, which is
            called the Interplanetary Magnetic Field (IMF). Geomagnetic
            storms are typically triggered due to high speed solar wind
            combined with a strong IMF in the southward direction
            (Z-component). Storm intensity increases as the Bz value
            becomes more negative.
        """)


solar_wind_section()
github_link()
