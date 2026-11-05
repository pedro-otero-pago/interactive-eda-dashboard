import pandas as pd


def load_energy(path):
    df = pd.read_csv(path)

    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time")

    df = df.loc[:, df.nunique() > 1]

    if "generation nuclear" in df.columns:
        df["generation nuclear"] = df["generation nuclear"].where(
            df["generation nuclear"] > 0
        )

    df = df.interpolate(method="time")

    return df

def _mask_frozen_readings(df, min_hours=24):
    readings = df[["temp", "humidity", "wind_speed"]]
    previous = readings.groupby(df["city_name"]).shift()
    repeated = readings.eq(previous).all(axis=1)

    run_id = (~repeated).cumsum()
    run_length = repeated.groupby(run_id).transform("sum")
    return repeated & (run_length >= min_hours)

def load_weather(path):
    df = pd.read_csv(path)

    df["city_name"] = df["city_name"].str.strip()
    df["time"] = pd.to_datetime(df["dt_iso"], utc=True)
    df = df.drop_duplicates(subset=["time", "city_name"])

    df["temp"] = df["temp"] - 273.15

    cols = [
        "temp", "humidity",
        "wind_speed", "wind_deg", "rain_1h", "clouds_all",
    ]
    df = df[["time", "city_name"] + cols].copy()

    df["humidity"] = df["humidity"].where(df["humidity"] > 0)
    df["wind_speed"] = df["wind_speed"].where(df["wind_speed"] <= 40)

    df = df.sort_values(["city_name", "time"])
    frozen = _mask_frozen_readings(df)
    df[cols] = df[cols].mask(frozen, axis=0)
    df[cols] = df.groupby("city_name")[cols].transform(
        lambda s: s.interpolate(limit_direction="both")
    )

    return df.set_index("time")


CITY_WEIGHTS = {
    "Madrid": 3266126,
    "Barcelona": 1636762,
    "Valencia": 794288,
    "Seville": 693229,
    "Bilbao": 334887,
}


def combine_datasets(energy, weather, weights=CITY_WEIGHTS):
    weather_cols = ["temp", "humidity", "wind_speed", "rain_1h", "clouds_all"]

    city_weights = weather["city_name"].map(weights)
    weighted = weather[weather_cols].mul(city_weights, axis=0)

    national_weather = (
        weighted.groupby(level="time")
        .sum()
        .div(city_weights.groupby(level="time").sum(), axis=0)
        .add_prefix("avg_")
    )

    return energy.join(national_weather, how="inner")