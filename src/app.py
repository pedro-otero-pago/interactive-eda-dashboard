import os

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis import LOCAL_TZ, aggregate, binned_mean, filter_dates, forecast_metrics, profile
from data_processing import combine_datasets, load_energy, load_weather

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
VARIABLES = {"Demand (MW)": "total load actual", "Price (€/MWh)": "price actual"}
BIN_WIDTH = 2


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
hourly = filter_dates(df, start, end)
data = aggregate(hourly, granularity)
errors = forecast_metrics(hourly)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Average demand", f"{hourly['total load actual'].mean():,.0f} MW")
col2.metric("Average price", f"{hourly['price actual'].mean():.1f} €/MWh")
col3.metric("Forecast error (MAPE)", f"{errors['mape']:.2f} %")
col4.metric("Average temperature", f"{hourly['avg_temp'].mean():.1f} °C")

overview_tab, patterns_tab, weather_tab = st.tabs(
    ["Overview", "Patterns", "Weather"]
)

with overview_tab:
    fig = px.line(
        data,
        y="total load actual",
        title=f"Electricity demand ({granularity} average)",
        labels={"total load actual": "Demand (MW)", "time": "Date"},
    )
    st.plotly_chart(fig)

    with st.expander("Show data"):
        st.dataframe(data)

with patterns_tab:
    label = st.radio("Variable", list(VARIABLES), horizontal=True)
    column = VARIABLES[label]

    left, right = st.columns(2)

    by_hour = profile(hourly, column, "hour")
    fig_hour = px.line(
        x=by_hour.index,
        y=by_hour.values,
        markers=True,
        title="Average by hour of the day",
        labels={"x": "Hour (Madrid time)", "y": label},
    )
    left.plotly_chart(fig_hour)

    by_day = profile(hourly, column, "weekday")
    fig_day = px.bar(
        x=[DAYS[i] for i in by_day.index],
        y=by_day.values,
        title="Average by day of the week",
        labels={"x": "Day", "y": label},
    )
    right.plotly_chart(fig_day)

with weather_tab:
    weather_label = st.radio(
        "Compare temperature with", list(VARIABLES), horizontal=True
    )
    weather_column = VARIABLES[weather_label]

    daily = aggregate(hourly, "day")
    curve = binned_mean(daily, "avg_temp", weather_column, BIN_WIDTH)

    fig_weather = px.scatter(
        daily,
        x="avg_temp",
        y=weather_column,
        opacity=0.35,
        title="Daily average temperature vs " + weather_label,
        labels={"avg_temp": "Average temperature (°C)", weather_column: weather_label},
    )
    fig_weather.add_trace(
        go.Scatter(
            x=curve.index + BIN_WIDTH / 2,
            y=curve.values,
            mode="lines+markers",
            name=f"Average per {BIN_WIDTH} °C",
        )
    )
    st.plotly_chart(fig_weather)