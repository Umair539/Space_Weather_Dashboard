import streamlit as st
import pandas as pd

st.title("Real Time Geomgagnetic Indices")

dst = pd.read_csv('data/transformed/dst.csv')
dst.loc[:, 'time'] = pd.to_datetime(dst['time'])

kp = pd.read_csv('data/transformed/kp.csv')
kp.loc[:, 'time'] = pd.to_datetime(kp['time'])

plasma = pd.read_csv('data/raw/plasma.csv')

min_val = 0
max_val_dst = len(dst) - 24

s_dst = st.slider(
    " ",
    min_val,
    max_val_dst,
    value = max_val_dst,
    step = 1,
    label_visibility = 'hidden'
    )

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        f"<div style='text-align: left;'>Displaying data from {dst['time'][s_dst]} to {dst['time'][s_dst+23]}</div>",
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        f"<div style='text-align: right;'>Data last updated at {plasma["time_tag"].iloc[-1]}</div>",
        unsafe_allow_html=True
    )

st.markdown(
    f"<div style='text-align: center;'><h3>Dst index</h3></div>", 
    unsafe_allow_html=True
    )

st.line_chart(
    data=dst.iloc[s_dst:s_dst+24],
    x='time',
    y='dst',
    x_label='Time',
    y_label='Dst (nT)',
    color="#ff0000"
)

with st.expander("More information on Dst index"):
    st.markdown("""
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
    """)

max_val_kp = len(kp) - 8
s_kp = st.slider(
    " ",
    min_val,
    max_val_kp,
    value = max_val_kp,
    step = 1,
    label_visibility = 'hidden'
    )

st.markdown(f'Displaying data from {kp['time'][s_kp]} to {kp['time'][s_kp+7]}')


st.markdown(
    f"<div style='text-align: center;'><h3>Kp index</h3></div>", 
    unsafe_allow_html=True
    )

st.line_chart(
    data=kp.iloc[s_kp:s_kp+8],
    x='time',
    y='Kp',
    x_label='Time',
    #y_label=label[str(feature)],
    color="#ff0000"
)

with st.expander("More information on Kp index"):
    st.markdown("""
        The Kp-index is a geomagnetic activity index based on data from 
        magnetometers around the world measured every 3 hours. The graph 
        above displays the observed Kp-value from the Planetary K-index
        of the NOAA SWPC and can be used to make a rough estimate of the 
        current global geomagnetic conditions. It is a quasi-logarithmic 
        index from 0 to 9 where a value of 5 indicates that a moderate storm is 
        occuring, a value of 7 indicate a severe storm is occuring, and
        a value of 9 indicates an extreme storm is occuring.
    """)