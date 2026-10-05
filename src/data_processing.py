import pandas as pd


def load_energy(path):
    df = pd.read_csv(path)

    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time")

    df = df.loc[:, df.nunique() > 1]

    df = df.interpolate(method="time")

    return df