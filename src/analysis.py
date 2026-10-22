import pandas as pd

FREQUENCIES = {"hour": "h", "day": "D", "week": "W", "month": "MS"}
LOCAL_TZ = "Europe/Madrid"


def aggregate(df, granularity):
    local = df.tz_convert(LOCAL_TZ)
    return local.resample(FREQUENCIES[granularity]).mean()


def filter_dates(df, start, end):
    local = df.tz_convert(LOCAL_TZ)
    mask = (local.index.date >= start) & (local.index.date <= end)
    return local[mask]


def profile(df, column, by):
    local = df.index.tz_convert(LOCAL_TZ)
    keys = {"hour": local.hour, "weekday": local.weekday, "month": local.month}
    return df[column].groupby(keys[by]).mean()


def forecast_metrics(df):
    error = df["total load forecast"] - df["total load actual"]
    return {
        "mean_error": error.mean(),
        "mae": error.abs().mean(),
        "mape": (error.abs() / df["total load actual"]).mean() * 100,
    }

def binned_mean(df, x, y, width):
    bins = (df[x] // width) * width
    return df[y].groupby(bins).mean()