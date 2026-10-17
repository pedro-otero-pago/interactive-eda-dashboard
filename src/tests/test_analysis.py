import datetime

import pandas as pd
import pytest

from analysis import aggregate, filter_dates, forecast_metrics, profile


def test_aggregate_uses_local_days():
    index = pd.date_range(
        "2015-12-31 23:00", periods=48, freq="h", tz="UTC", name="time"
    )
    df = pd.DataFrame({"price": [10.0] * 24 + [20.0] * 24}, index=index)

    result = aggregate(df, "day")

    assert result["price"].tolist() == [10.0, 20.0]


def test_profile_by_hour_averages_each_hour_across_days():
    index = pd.date_range(
        "2015-12-31 23:00", periods=48, freq="h", tz="UTC", name="time"
    )
    values = [float(h) for h in range(24)] + [float(h + 10) for h in range(24)]
    df = pd.DataFrame({"load": values}, index=index)

    result = profile(df, "load", "hour")

    assert len(result) == 24
    assert result.loc[0] == 5.0
    assert result.loc[23] == 28.0


def test_profile_by_weekday_starts_on_monday():
    index = pd.date_range(
        "2016-01-03 23:00", periods=48, freq="h", tz="UTC", name="time"
    )
    df = pd.DataFrame({"load": [1.0] * 24 + [3.0] * 24}, index=index)

    result = profile(df, "load", "weekday")

    assert result.to_dict() == {0: 1.0, 1: 3.0}


def test_forecast_metrics():
    df = pd.DataFrame(
        {
            "total load actual": [100.0, 200.0],
            "total load forecast": [110.0, 190.0],
        }
    )

    result = forecast_metrics(df)

    assert result["mean_error"] == pytest.approx(0.0)
    assert result["mae"] == pytest.approx(10.0)
    assert result["mape"] == pytest.approx(7.5)


def test_filter_dates_keeps_whole_local_days():
    index = pd.date_range(
        "2015-12-31 23:00", periods=72, freq="h", tz="UTC", name="time"
    )
    df = pd.DataFrame({"load": range(72)}, index=index)

    result = filter_dates(df, datetime.date(2016, 1, 2), datetime.date(2016, 1, 2))

    assert len(result) == 24
    assert result.index[0].hour == 0
    assert result["load"].iloc[0] == 24