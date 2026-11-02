import pandas as pd
import pytest

from model import model_scores, train_model


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