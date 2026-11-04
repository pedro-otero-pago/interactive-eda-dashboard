import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from evaluation import mae, rmse, split_by_year
from features import build_dataset


def train_model(X_train, y_train):
    model = HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.05,
        early_stopping=False,
        random_state=0,
    )
    model.fit(X_train, y_train)
    return model


def model_scores(model, X, y):
    predictions = pd.Series(model.predict(X), index=y.index)
    return {"MAE": mae(y, predictions), "RMSE": rmse(y, predictions)}


def predict_test_year(df, test_year=2018):
    X, y = build_dataset(df)
    X_train, X_test, y_train, y_test = split_by_year(X, y, test_year)
    model = train_model(X_train, y_train)
    return pd.DataFrame(
        {
            "Actual": y_test,
            "Model": model.predict(X_test),
            "Yesterday": X_test["price_lag_24"],
            "Last week": X_test["price_lag_168"],
        }
    )