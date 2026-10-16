## Project structure

- `data/` — the Spain energy and weather datasets from Kaggle ("Hourly
  energy demand, generation and weather", CC0), stored gzip-compressed
  (`.csv.gz`) so the repository stays small and nothing has to be
  downloaded to run the project.
- `data_processing.py` — loads and cleans both datasets.
  - `load_energy` converts the timestamps to a UTC datetime index, drops columns that are empty or constant, and fills the few missing hours with time-based interpolation. 
  - `load_weather` removes duplicated hour-city rows, strips the city names, converts temperatures from Kelvin to Celsius, turns impossible values into gaps and interpolates them per city, and drops the unreliable pressure column.
  - `combine_datasets` merges both sources into one hourly table, using the mean of the five cities as national weather.
  - Cleaning also drops impossible nuclear zeros and weather readings
  frozen for 24 hours or more.
- `src/analysis.py`: aggregation by hour/day/week/month in Madrid
  time, average profiles, and forecast error metrics.

## Running tests

    python -m pytest -v

Run from the project root with the virtual environment activated. The
tests cover the cleaned real dataset (shape, index, missing values,
constant columns) and the interpolation logic on a small synthetic file.