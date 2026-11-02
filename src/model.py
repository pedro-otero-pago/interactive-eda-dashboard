import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from evaluation import mae, rmse


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