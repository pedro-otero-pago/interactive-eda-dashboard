import os

import streamlit as st

from analysis import LOCAL_TZ, aggregate, filter_dates
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

local_index = df.index.tz_convert(LOCAL_TZ)
min_date = local_index.min().date()
max_date = local_index.max().date()

st.sidebar.header("Filters")
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
granularity = st.sidebar.selectbox(
    "Granularity", ["hour", "day", "week", "month"], index=1
)

if len(date_range) != 2:
    st.info("Select both a start and an end date.")
    st.stop()

start, end = date_range
data = aggregate(filter_dates(df, start, end), granularity)

st.write(f"{len(data):,} rows ({granularity}) from {start} to {end}")
st.dataframe(data.head(100))