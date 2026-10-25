## Project structure

- `data/` — the Spain energy and weather datasets from Kaggle ("Hourly
  energy demand, generation and weather", CC0), stored gzip-compressed
  (`.csv.gz`) so the repository stays small and nothing has to be
  downloaded to run the project.
- `src/data_processing.py` — loads and cleans both datasets.
  - `load_energy` converts the timestamps to a UTC datetime index,
    drops columns that are empty or constant, treats impossible
    nuclear zeros as sensor failures, and fills the few missing hours
    with time-based interpolation.
  - `load_weather` removes duplicated hour-city rows, strips the city
    names, converts temperatures from Kelvin to Celsius, turns
    impossible or frozen readings (identical for 24 hours or more)
    into gaps and interpolates them per city, and drops the unreliable
    pressure column.
  - `combine_datasets` merges both sources into one hourly table,
    using the mean of the five cities as national weather.
- `src/analysis.py` — date filtering, aggregation by
  hour/day/week/month in Madrid time, average profiles, binned
  averages, generation mix grouping, and forecast error metrics.
- `src/app.py` — Streamlit app. Loads and caches the data, has
  sidebar filters for the date range and the granularity, shows KPI
  cards, and has five tabs: demand overview, average profiles by
  hour and weekday, temperature vs demand or price, generation mix,
  and the quality of the official demand forecast.

## Running the dashboard

From the repository root, with the virtual environment active:

    streamlit run src/app.py

It opens at http://localhost:8501.

## Running tests

    python -m pytest -v

Run from the project root with the virtual environment activated. The
tests cover the cleaned real datasets (shape, index, missing values,
plausible ranges), the cleaning and combination rules on small
synthetic files, and the analysis functions on hand-built tables.