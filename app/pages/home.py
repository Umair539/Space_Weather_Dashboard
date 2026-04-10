import streamlit as st
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
from utils import safe_query, data_last_synced, init_db, is_data_fresh
import altair as alt
from utils import get_noaa_advisory
from datetime import timedelta

conn = init_db()
synced = is_data_fresh(conn)

st.title("Space Weather Dashboard 🪐")

st.markdown(
    """
    This Space Weather Dashboard provides near real time data on key
    space environment properties, including solar wind parameters and
    geomagnetic indices, collected from the
    [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov).
    """
)

st.markdown(
    f"<div style='text-align: right; font-style: italic; color: gray;'>"
    f"{data_last_synced(conn)}"
    f"</div>",
    unsafe_allow_html=True,
)

dst = safe_query(
    conn, "SELECT time, dst, predictions FROM dst ORDER BY time DESC LIMIT 24"
)
kp = safe_query(conn, "SELECT * FROM kp ORDER BY time DESC LIMIT 1")

c1, c2 = st.columns((0.5, 0.5))

with c1:
    start_time = dst["time"].iloc[0]
    end_time = start_time + timedelta(hours=1)
    st.markdown("")
    st.markdown(
        f'<div style="font-size: 24px; text-align: center; margin-top: 20px;">'
        f"Predicted Dst for {start_time.strftime('%d %b, %H:%M')}–{end_time.strftime('%H:%M')} UTC: "
        f"{dst['predictions'].iloc[0].round(2)} nT</div>",
        unsafe_allow_html=True,
    )

    dst_chart = (
        alt.Chart(dst)
        .transform_fold(
            ["dst", "predictions"],
            as_=["Series", "Value"],
        )
        .mark_line()
        .encode(
            x=alt.X(
                "time:T",
                axis=alt.Axis(
                    labelAngle=0,
                    tickCount=6,
                    format="%d %b %H:%M",
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
                    labelExpr="datum.label == 'dst' ? 'Observed Dst' : datum.label == 'predictions' ? 'Model Prediction' : datum.label",
                ),
            ),
        )
    )

    st.altair_chart(dst_chart, width="stretch")

with c2:
    step_colours = [
        {"range": [0, 5.0], "color": "green"},
        {"range": [5.0, 7.0], "color": "orange"},
        {"range": [7.0, 9.0], "color": "red"},
    ]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=kp["Kp"].iloc[0],
            number={"prefix": "Kp: "},
            title={"text": "Kp Index", "font": {"size": 24}},
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 9]},
                "steps": step_colours,
                "bar": {"color": "rgba(0, 0, 0, 0)"},
                "threshold": {
                    "line": {"color": "black", "width": 3},
                    "value": kp["Kp"].iloc[0],
                    "thickness": 1,
                },
            },
        )
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")

st.subheader("Official SWPC Advisory")

advisory_text = get_noaa_advisory()

# Using a container with a border for a "Report" look
with st.container(border=True):
    st.text(advisory_text)

st.caption("Source: NOAA/SWPC Advisory Outlook")

if synced:
    st_autorefresh(60000)
else:
    st_autorefresh(5000)
