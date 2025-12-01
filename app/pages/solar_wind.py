import streamlit as st
import pandas as pd

st.title("Real Time Solar Wind Properties")

solar = pd.read_csv('data/transformed/solar.csv')
solar.loc[:, 'time_tag'] = pd.to_datetime(solar['time_tag']) 
solar.set_index('time_tag', inplace=True)

solar_agg = pd.read_csv('data/transformed/solar.csv')
solar_agg.loc[:, 'time_tag'] = pd.to_datetime(solar_agg['time_tag']) 
solar_agg.set_index('time_tag', inplace=True)

feature = st.selectbox(
    label = 'Select feature',
    options = solar_agg.columns[:],
    index = 0
)

st.dataframe(
    solar_agg[[str(feature)]]
)

min_epoch = 0
max_epoch = len(solar_agg)-24*60
s = st.slider(
    "",
    min_epoch,
    max_epoch,
    step = 1,
    label_visibility='hidden'
    )


st.line_chart(
    solar_agg[[str(feature)]].iloc[s:s+24*60]
)