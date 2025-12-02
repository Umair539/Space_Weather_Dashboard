import streamlit as st
import pandas as pd

st.title("Real Time Geomgagnetic Indices")

dst = pd.read_csv('data/transformed/dst.csv')
dst.loc[:, 'time'] = pd.to_datetime(dst['time'])

kp = pd.read_csv('data/transformed/kp.csv')
kp.loc[:, 'time'] = pd.to_datetime(kp['time']) 

min_val = 0
max_val_dst = len(dst) - 24
max_val_kp = len(kp) - 8

s_dst = st.slider(
    " ",
    min_val,
    max_val_dst,
    value = max_val_dst,
    step = 1,
    label_visibility = 'hidden'
    )

st.markdown(f'{dst['time'][s_dst]} to {dst['time'][s_dst+23]}')

st.markdown(
    f"<div style='text-align: center;'><h3>DST index</h3></div>", 
    unsafe_allow_html=True
    )

st.line_chart(
    data=dst.iloc[s_dst:s_dst+24],
    x='time',
    y='dst',
    x_label='Time',
    #y_label=label[str(feature)],
    color="#ff0000"
)

s_kp = st.slider(
    " ",
    min_val,
    max_val_kp,
    value = max_val_kp,
    step = 1,
    label_visibility = 'hidden'
    )

st.markdown(f'{kp['time'][s_kp]} to {kp['time'][s_kp+7]}')


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