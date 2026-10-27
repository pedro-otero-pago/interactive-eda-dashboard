import pandas as pd

from analysis import LOCAL_TZ


def split_by_year(X, y, test_year):
    is_test = X.index.tz_convert(LOCAL_TZ).year >= test_year
    return X[~is_test], X[is_test], y[~is_test], y[is_test]


def mae(y_true, y_pred):
    return float((y_true - y_pred).abs().mean())


def rmse(y_true, y_pred):
    return float(((y_true - y_pred) ** 2).mean() ** 0.5)


def baseline_scores(X, y, market_price):
    predictions = {
        "Yesterday, same hour": X["price_lag_24"],
        "Last week, same hour": X["price_lag_168"],
        "Market day-ahead price": market_price,
    }
    return pd.DataFrame(
        {
            name: {"MAE": mae(y, pred), "RMSE": rmse(y, pred)}
            for name, pred in predictions.items()
        }
    ).T