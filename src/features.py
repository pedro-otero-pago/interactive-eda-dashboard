import pandas as pd

from analysis import LOCAL_TZ

TARGET = "price actual"
FEATURES = [
    "price_lag_24",
    "price_lag_168",
    "load_forecast",
    "solar_forecast",
    "wind_forecast",
    "hour",
    "weekday",
    "month",
]


def build_dataset(df):
    features = pd.DataFrame(index=df.index)
    features["price_lag_24"] = df[TARGET].shift(24)
    features["price_lag_168"] = df[TARGET].shift(168)
    features["load_forecast"] = df["total load forecast"]
    features["solar_forecast"] = df["forecast solar day ahead"]
    features["wind_forecast"] = df["forecast wind onshore day ahead"]

    local = df.index.tz_convert(LOCAL_TZ)
    features["hour"] = local.hour
    features["weekday"] = local.weekday
    features["month"] = local.month

    features = features.dropna()
    return features[FEATURES], df.loc[features.index, TARGET]