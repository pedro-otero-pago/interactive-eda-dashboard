import os

import pandas as pd

from data_processing import load_energy
from features import FEATURES, build_dataset

ENERGY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "energy_dataset.csv.gz"
)


def make_frame(hours=300):
    index = pd.date_range(
        "2016-01-01", periods=hours, freq="h", tz="UTC", name="time"
    )
    return pd.DataFrame(
        {
            "price actual": [float(i) for i in range(hours)],
            "total load forecast": 30000.0,
            "forecast solar day ahead": 1000.0,
            "forecast wind onshore day ahead": 2000.0,
        },
        index=index,
    )


def test_price_lags_are_24_and_168_hours_back():
    X, y = build_dataset(make_frame())

    assert len(X) == 300 - 168
    assert (X["price_lag_24"] == y - 24).all()
    assert (X["price_lag_168"] == y - 168).all()


def test_features_never_use_the_current_or_future_price():
    df = make_frame()
    changed = df.copy()
    changed.iloc[180, changed.columns.get_loc("price actual")] = 9999.0
    moment = df.index[180]

    before, _ = build_dataset(df)
    after, _ = build_dataset(changed)

    pd.testing.assert_frame_equal(before.loc[:moment], after.loc[:moment])
    next_day = moment + pd.Timedelta(hours=24)
    assert after.loc[next_day, "price_lag_24"] == 9999.0


def test_features_have_the_expected_columns_and_no_gaps():
    X, y = build_dataset(make_frame())

    assert list(X.columns) == FEATURES
    assert X.isna().sum().sum() == 0
    assert len(X) == len(y)


def test_real_dataset_gives_the_expected_table():
    X, y = build_dataset(load_energy(ENERGY_PATH))

    assert X.shape == (35064 - 168, len(FEATURES))
    assert X.isna().sum().sum() == 0