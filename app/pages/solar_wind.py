import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

st_autorefresh(30000)

st.title("Real Time Solar Wind Properties")

solar = pd.read_csv('data/transformed/solar.csv')
solar.loc[:, 'time'] = pd.to_datetime(solar['time']) 

solar_agg = pd.read_csv('data/transformed/solar_agg.csv')
solar_agg.loc[:, 'time'] = pd.to_datetime(solar_agg['time']) 

col1, col2, col3 = st.columns(3)

with col1:
    resolution = st.selectbox(
        label = 'Select time resolution',
        options = ['Minutely', 'Hourly'],
        index = 0
    )

columns = solar.columns.str.title()[1:]

with col2:
    features = st.multiselect(
        label = 'Select features',
        options = columns,
        default = columns[:2]
    )
    
with col3:
    aggregation = st.selectbox(
        label = 'Select aggregation method',
        options = ['Mean', 'Standard deviation', 'Interquartile range'],
        disabled = (resolution == 'Minutely')
    )

if resolution == 'Hourly':
    suffix = {
        'Mean':'_mean',
        'Standard deviation':'_std',
        'Interquartile range':'_iqr'
    }
    filtered_cols = [col for col in solar_agg.columns if col.endswith(suffix[aggregation])]
    df = solar_agg[['time'] + filtered_cols]
    rename_mapping = {col: col.replace(suffix[aggregation], '') for col in filtered_cols}
    df = df.rename(columns=rename_mapping)
else:
    df = solar

win = {
    'Minutely': 24*60,
    'Hourly': 24
}

min_val = 0
max_val = len(df)-win[resolution] + (-1 if resolution == 'Hourly' else 0)

s = st.slider(
    " ",
    min_val,
    max_val,
    value = max_val,
    step = 1,
    label_visibility = 'hidden'
    )

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        f"<div style='text-align: left;'>Displaying data from {df['time'][s]} to {df['time'][s+win[resolution]-1]}</div>",
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        f"<div style='text-align: right;'>Data last updated at {solar["time"].iloc[-1]}</div>",
        unsafe_allow_html=True
    )

label = {
    'Density':"Particle density (n/cm3)",
    'Speed':'Solar wind speed (km/s)',
    'Temperature':'Solar wind temperature (K)',
    'Pressure':'Solar wind dynamic pressure (nPa)',
    'Bz':'IMF Z-component (nT)',
    'Bt': 'IMF magnitude (nT)'
}

for feature in features:
    
    st.markdown(
        f"<div style='text-align: center;'><h3>Solar Wind {feature}</h3></div>", 
        unsafe_allow_html=True
        )
    
    st.line_chart(
        data=df.iloc[s:s+win[resolution]],
        x='time',
        y=str(feature.lower()),
        x_label='Time',
        y_label=label[str(feature)],
        color="#ff0000"
    )
    
with st.expander("More information on Solar Wind"):
    st.markdown("""
        The solar wind is a continuous stream of charged particles
        (plasma) emmited by the Sun's atmosphere. When this stream 
        of particles reaches Earth, it transfers energy into the Earth's 
        magnetosphere. Solar wind is made up of two components: the 
        properties of the plasma (e.g. speed and density), and the 
        properties of the embedded magnetic field, which is 
        called the Interplanetary Magnetic Field (IMF). Geomganetic 
        storms are typically triggered due to high speed solar wind 
        combined with a strong IMF in the southward direction 
        (Z-component). Storm intensity increases as the Bz value 
        becomes more negative.
    """)