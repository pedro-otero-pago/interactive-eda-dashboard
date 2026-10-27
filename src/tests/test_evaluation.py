import pandas as pd
import pytest

from evaluation import baseline_scores, mae, rmse, split_by_year


def test_split_by_year_is_chronological_and_uses_local_years():
    index = pd.date_range("2017-12-30", periods=96, freq="h", tz="UTC")
    X = pd.DataFrame({"a": range(96)}, index=index)
    y = pd.Series(range(96), index=index)

    X_train, X_test, y_train, y_test = split_by_year(X, y, 2018)

    assert X_train.index.max() < X_test.index.min()
    assert len(X_train) == 47
    assert len(X_test) == 49
    assert len(y_train) == 47
    assert len(y_test) == 49


def test_mae_and_rmse():
    y_true = pd.Series([10.0, 20.0])
    y_pred = pd.Series([12.0, 17.0])

    assert mae(y_true, y_pred) == pytest.approx(2.5)
    assert rmse(y_true, y_pred) == pytest.approx(6.5**0.5)


def test_baseline_scores_are_computed_for_each_prediction():
    index = pd.date_range("2018-01-01", periods=2, freq="h", tz="UTC")
    X = pd.DataFrame(
        {"price_lag_24": [10.0, 20.0], "price_lag_168": [12.0, 24.0]},
        index=index,
    )
    y = pd.Series([10.0, 20.0], index=index)
    market = pd.Series([11.0, 19.0], index=index)

    scores = baseline_scores(X, y, market)

    assert list(scores.columns) == ["MAE", "RMSE"]
    assert scores.loc["Yesterday, same hour", "MAE"] == 0.0
    assert scores.loc["Last week, same hour", "MAE"] == pytest.approx(3.0)
    assert scores.loc["Market day-ahead price", "MAE"] == pytest.approx(1.0)