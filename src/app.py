import os

import streamlit as st

from data_processing import combine_datasets, load_energy, load_weather

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@st.cache_data
def load_data():
    energy = load_energy(os.path.join(DATA_DIR, "energy_dataset.csv.gz"))
    weather = load_weather(os.path.join(DATA_DIR, "weather_features.csv.gz"))
    return combine_datasets(energy, weather)


st.set_page_config(page_title="Spain Energy Dashboard", layout="wide")
st.title("Spain energy demand, generation and weather")

df = load_data()

st.write(
    f"{len(df):,} hourly rows from {df.index.min():%Y-%m-%d} "
    f"to {df.index.max():%Y-%m-%d}"
)
st.dataframe(df.head(100))