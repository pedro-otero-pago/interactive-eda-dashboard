import pandas as pd


def load_energy(path):
    df = pd.read_csv(path)

    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time")

    df = df.loc[:, df.nunique() > 1]

    df = df.interpolate(method="time")

    return df

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
    df[cols] = df.groupby("city_name")[cols].transform(
        lambda s: s.interpolate(limit_direction="both")
    )

    return df.set_index("time")