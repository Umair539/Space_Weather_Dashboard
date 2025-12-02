import streamlit as st
import pandas as pd

st.title("Real Time Geomgagnetic Indices")

dst = pd.read_csv('data/raw/dst.csv')
dst.loc[:, ]