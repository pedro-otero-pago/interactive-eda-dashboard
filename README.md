## Project structure

- `data/` — the Spain energy and weather datasets from Kaggle ("Hourly
  energy demand, generation and weather", CC0), stored gzip-compressed
  (`.csv.gz`) so the repository stays small and nothing has to be
  downloaded to run the project.
- `data_processing.py` — loads the energy dataset and cleans it:
  converts the timestamps to a UTC datetime index, drops columns that
  are empty or constant, and fills the few missing hours with time-based
  interpolation.

## Running tests

    python -m pytest -v

Run from the project root with the virtual environment activated. The
tests cover the cleaned real dataset (shape, index, missing values,
constant columns) and the interpolation logic on a small synthetic file.