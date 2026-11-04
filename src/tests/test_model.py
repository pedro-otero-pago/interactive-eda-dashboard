import pandas as pd
import pytest

from model import model_scores, predict_test_year, train_model


class PerfectModel:
    def predict(self, X):
        return X["hour"].to_numpy() * 10.0


def make_data(rows=480):
    index = pd.date_range("2016-01-01", periods=rows, freq="h", tz="UTC")
    hours = [i % 24 for i in range(rows)]
    X = pd.DataFrame({"hour": hours}, index=index)
    y = pd.Series([h * 10.0 for h in hours], index=index)
    return X, y


def test_model_scores_are_zero_for_perfect_predictions():
    X, y = make_data()

    scores = model_scores(PerfectModel(), X, y)

    assert scores == {"MAE": 0.0, "RMSE": 0.0}


def test_train_model_learns_a_simple_hourly_pattern():
    X, y = make_data()

    model = train_model(X, y)
    scores = model_scores(model, X, y)

    assert scores["MAE"] < 5.0

def test_predict_test_year_only_returns_the_test_year():
    index = pd.date_range(
        "2016-12-31 23:00", periods=2 * 365 * 24, freq="h", tz="UTC", name="time"
    )
    prices = [float(i % 24) * 10.0 for i in range(len(index))]
    df = pd.DataFrame(
        {
            "price actual": prices,
            "total load forecast": 30000.0,
            "forecast solar day ahead": 1000.0,
            "forecast wind onshore day ahead": 2000.0,
        },
        index=index,
    )

    results = predict_test_year(df, 2018)

    assert list(results.columns) == ["Actual", "Model", "Yesterday", "Last week"]
    assert set(results.index.tz_convert("Europe/Madrid").year) == {2018}
    assert (results["Actual"] - results["Model"]).abs().mean() < 5.0