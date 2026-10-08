import os

import pandas as pd
import pytest
from data_processing import load_energy, load_weather

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "energy_dataset.csv.gz")
WEATHER_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "weather_features.csv.gz")



@pytest.fixture(scope="module")
def df():
    return load_energy(DATA_PATH)

@pytest.fixture(scope="module")
def weather():
    return load_weather(WEATHER_PATH)


def test_shape(df):
    assert df.shape == (35064, 20)


def test_index_is_utc_datetime(df):
    assert isinstance(df.index, pd.DatetimeIndex)
    assert str(df.index.tz) == "UTC"


def test_index_is_sorted_and_unique(df):
    assert df.index.is_monotonic_increasing
    assert df.index.is_unique


def test_no_missing_values(df):
    assert df.isna().sum().sum() == 0


def test_no_constant_or_empty_columns(df):
    assert (df.nunique() > 1).all()


def test_interpolates_gaps_and_drops_constant_columns(tmp_path):
    csv_path = tmp_path / "energy.csv"
    pd.DataFrame(
        {
            "time": [f"2015-01-01 0{h}:00:00+01:00" for h in range(5)],
            "price": [10.0, 20.0, None, 40.0, 50.0],
            "load": [1.0, 2.0, 3.0, 4.0, 5.0],
            "always_zero": [0.0, 0.0, 0.0, 0.0, 0.0],
        }
    ).to_csv(csv_path, index=False)

    result = load_energy(csv_path)

    assert result["price"].iloc[2] == pytest.approx(30.0)
    assert "always_zero" not in result.columns

def test_weather_shape(weather):
    assert weather.shape == (175320, 7)


def test_weather_index_is_utc_datetime(weather):
    assert isinstance(weather.index, pd.DatetimeIndex)
    assert str(weather.index.tz) == "UTC"


def test_weather_cities_are_clean_and_complete(weather):
    counts = weather["city_name"].value_counts()
    assert set(counts.index) == {
        "Barcelona", "Bilbao", "Madrid", "Seville", "Valencia"
    }
    assert (counts == 35064).all()


def test_weather_no_missing_values(weather):
    assert weather.isna().sum().sum() == 0


def test_weather_values_are_plausible(weather):
    assert weather["temp"].between(-20, 50).all()
    assert (weather["humidity"] > 0).all()
    assert (weather["wind_speed"] <= 40).all()


def test_load_weather_cleans_small_file(tmp_path):
    csv_path = tmp_path / "weather.csv"
    hours = [0, 1, 1, 2, 3]
    pd.DataFrame(
        {
            "dt_iso": [f"2015-01-01 0{h}:00:00+01:00" for h in hours],
            "city_name": [" Madrid"] * 5,
            "temp": [283.15] * 5,
            "pressure": [1015] * 5,
            "humidity": [50, 60, 60, 0, 80],
            "wind_speed": [2] * 5,
            "wind_deg": [180] * 5,
            "rain_1h": [0.0] * 5,
            "clouds_all": [20] * 5,
        }
    ).to_csv(csv_path, index=False)

    result = load_weather(csv_path)

    assert len(result) == 4
    assert set(result["city_name"]) == {"Madrid"}
    assert result["temp"].iloc[0] == pytest.approx(10.0)
    assert result["humidity"].iloc[2] == pytest.approx(70.0)
    assert "pressure" not in result.columns