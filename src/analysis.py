import pandas as pd

FREQUENCIES = {"hour": "h", "day": "D", "week": "W", "month": "MS"}
LOCAL_TZ = "Europe/Madrid"

MIX_GROUPS = {
    "Nuclear": ["generation nuclear"],
    "Gas": ["generation fossil gas"],
    "Coal": [
        "generation fossil brown coal/lignite",
        "generation fossil hard coal",
    ],
    "Hydro": [
        "generation hydro run-of-river and poundage",
        "generation hydro water reservoir",
    ],
    "Wind": ["generation wind onshore"],
    "Solar": ["generation solar"],
    "Other": [
        "generation biomass",
        "generation fossil oil",
        "generation other",
        "generation other renewable",
        "generation waste",
    ],
}


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


def binned_mean(df, x, y, width):
    bins = (df[x] // width) * width
    return df[y].groupby(bins).mean()


def generation_mix(df):
    return pd.DataFrame(
        {name: df[cols].sum(axis=1) for name, cols in MIX_GROUPS.items()}
    )


def forecast_errors(df):
    error = df["total load forecast"] - df["total load actual"]
    return pd.DataFrame(
        {
            "error": error,
            "abs_pct_error": error.abs() / df["total load actual"] * 100,
        }
    )


def forecast_metrics(df):
    error = df["total load forecast"] - df["total load actual"]
    return {
        "mean_error": error.mean(),
        "mae": error.abs().mean(),
        "mape": (error.abs() / df["total load actual"]).mean() * 100,
    }