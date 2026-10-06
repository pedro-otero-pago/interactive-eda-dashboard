import os

import pandas as pd
import pytest
from data_processing import load_energy

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "energy_dataset.csv.gz")


@pytest.fixture(scope="module")
def df():
    return load_energy(DATA_PATH)


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