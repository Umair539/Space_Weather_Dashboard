import streamlit as st
import altair as alt
import pandas as pd
import plotly.graph_objects as go
from app_utils import (
    data_last_synced,
    init_db,
    get_latest_timestamp,
    cached_query,
    get_noaa_advisory,
)

conn = init_db()

st.title("Space Weather Dashboard 🪐")

st.markdown(
    """
    This Space Weather Dashboard provides frequently updated data on key
    space environment properties, including solar wind parameters and
    geomagnetic indices, collected from the
    [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov).
    """
)


def _kp_severity(k):
    if k >= 8:
        return "Extreme", "#9d1a8a"
    if k >= 7:
        return "Severe", "#c93030"
    if k >= 5:
        return "Moderate", "#e05d0b"
    if k >= 4:
        return "Minor", "#d29922"
    return "Quiet", "#2ea043"


def _dst_severity(d):
    if d <= -200:
        return "Extreme", "#9d1a8a"
    if d <= -100:
        return "Severe", "#c93030"
    if d <= -50:
        return "Moderate", "#e05d0b"
    if d <= -30:
        return "Minor", "#d29922"
    return "Quiet", "#2ea043"


def _sw_severity(speed):
    if speed >= 600:
        return "Severe", "#c93030"
    if speed >= 500:
        return "Moderate", "#e05d0b"
    if speed >= 450:
        return "Minor", "#d29922"
    return "Quiet", "#2ea043"


def _bz_severity(bz):
    if bz <= -20:
        return "Severe", "#c93030"
    if bz <= -10:
        return "Moderate", "#e05d0b"
    if bz <= -5:
        return "Minor", "#d29922"
    return "Quiet", "#2ea043"


def _metric_card(label, value, unit, status, color):
    return f"""
    <div style="
        background: linear-gradient(135deg, {color}22 0%, #161b2280 100%);
        border: 1px solid {color}55;
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    ">
        <div style="font-size:11px; color:#8b949e; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">{label}</div>
        <div style="font-size:30px; font-weight:700; color:{color}; line-height:1.1;">{value}<span style="font-size:14px; color:#8b949e; margin-left:3px;">{unit}</span></div>
        <div style="font-size:11px; color:{color}; margin-top:5px; text-transform:uppercase; letter-spacing:0.5px;">{status}</div>
    </div>
    """


@st.fragment(run_every=120)
def home_section():
    latest_ts_dst = get_latest_timestamp(conn, "dst_predictions")
    latest_ts_kp = get_latest_timestamp(conn, "kp")
    latest_ts_solar = get_latest_timestamp(conn, "solar")

    st.markdown(
        f"<div style='text-align: right; font-style: italic; color: gray;'>"
        f"{data_last_synced(conn)}"
        f"</div>",
        unsafe_allow_html=True,
    )

    dst_query = """
        SELECT p.time, d.dst, p.dst_predictions
        FROM dst_predictions p
        LEFT JOIN dst d ON p.time = d.time
        ORDER BY p.time DESC
        LIMIT 169
    """
    dst = cached_query(conn, dst_query, latest_ts_dst)
    kp = cached_query(conn, "SELECT * FROM kp ORDER BY time DESC LIMIT 1", latest_ts_kp)
    dst_now = cached_query(
        conn,
        "SELECT dst FROM dst WHERE dst IS NOT NULL ORDER BY time DESC LIMIT 1",
        latest_ts_dst,
    )
    solar_latest = cached_query(
        conn,
        "SELECT speed, bz FROM solar ORDER BY time DESC LIMIT 1",
        latest_ts_solar,
    )

    kp_val = float(kp["Kp"].iloc[0])
    dst_val = float(dst_now["dst"].iloc[0])
    sw_speed = float(solar_latest["speed"].iloc[0])
    imf_bz = float(solar_latest["bz"].iloc[0])

    # Grab values needed for titles before sorting
    start_time = dst["time"].iloc[0]
    next_pred = dst["dst_predictions"].iloc[0].round(2)
    dst = dst.sort_values("time")
    kp_status, kp_color = _kp_severity(kp_val)

    # Title row
    t1, t2 = st.columns((0.5, 0.5))
    with t1:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div style="font-size:24px;">Dst Index — Last 7 Days</div>'
            f'<div style="font-size:14px; color:#8b949e; margin-top:4px;">'
            f'Predicted: {next_pred} nT | {start_time.strftime("%d %b, %H:%M")} UTC'
            f"</div></div>",
            unsafe_allow_html=True,
        )
    with t2:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div style="font-size:24px;">Kp Index</div>'
            f'<div style="font-size:14px; color:{kp_color}; margin-top:4px; text-transform:uppercase; letter-spacing:1px;">'
            f"{kp_status}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # Chart row
    c1, c2 = st.columns((0.5, 0.5))

    with c1:
        dst_vals = pd.concat([dst["dst"], dst["dst_predictions"]]).dropna()
        y_min_dst = float(dst_vals.min()) - 5
        y_max_dst = float(dst_vals.max()) + 5

        dst_chart = (
            alt.Chart(dst)
            .transform_fold(["dst", "dst_predictions"], as_=["Series", "Value"])
            .mark_line()
            .encode(
                x=alt.X(
                    "time:T",
                    axis=alt.Axis(
                        labelAngle=0, tickCount=6, format="%d %b", title="Time"
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
        )
        st.altair_chart(dst_chart.properties(height=400), width="stretch")

    with c2:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=kp_val,
                number={
                    "font": {"size": 52, "color": kp_color, "family": "sans-serif"},
                },
                gauge={
                    "shape": "angular",
                    "axis": {
                        "range": [0, 9],
                        "tickvals": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                        "ticktext": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                        "tickfont": {"color": "#8b949e", "size": 11},
                        "tickcolor": "#30363d",
                        "tickwidth": 1,
                    },
                    "steps": [
                        {"range": [0, 4], "color": "#0d2b0d"},
                        {"range": [4, 5], "color": "#2d2200"},
                        {"range": [5, 7], "color": "#2d1500"},
                        {"range": [7, 8], "color": "#2d0000"},
                        {"range": [8, 9], "color": "#200020"},
                    ],
                    "bar": {"color": kp_color, "thickness": 0.25},
                    "bgcolor": "#0d1117",
                    "borderwidth": 0,
                },
            )
        )
        fig.update_layout(
            height=350,
            paper_bgcolor="#0d1117",
            font={"color": "#e6edf3", "family": "sans-serif"},
            margin={"t": 20, "b": 10, "l": 40, "r": 40},
        )
        st.plotly_chart(fig, width="stretch")

    # Metric cards below plots
    dst_status, dst_color = _dst_severity(dst_val)
    sw_status, sw_color = _sw_severity(sw_speed)
    bz_status, bz_color = _bz_severity(imf_bz)

    metrics = [
        ("Kp Index", f"{kp_val:.2f}", "", kp_status, kp_color),
        ("Dst Index", f"{dst_val:+.0f}", "nT", dst_status, dst_color),
        ("Solar Wind", f"{sw_speed:.0f}", "km/s", sw_status, sw_color),
        ("IMF Bz", f"{imf_bz:+.1f}", "nT", bz_status, bz_color),
    ]
    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    for col, (label, value, unit, status, color) in zip(st.columns(4), metrics):
        with col:
            st.markdown(
                _metric_card(label, value, unit, status, color), unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)


@st.fragment(run_every=3600)
def advisory_section():
    st.subheader("Official SWPC Advisory")
    with st.container(border=True):
        st.text(get_noaa_advisory())
    st.caption("Source: NOAA/SWPC Advisory Outlook")


home_section()
advisory_section()
