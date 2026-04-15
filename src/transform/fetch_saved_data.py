import pandas as pd
from src.utils.parser import parse_data
from src.utils.r2 import R2Client


def fetch_saved_data(folder_path):
    r2 = R2Client()
    dfs = []
    time_col = None

    for fname in ["lists.json", "dicts.json"]:
        key = f"{folder_path}/{fname}"
        raw = r2.download_json(key)

        if not raw:
            continue

        parsed = parse_data(raw)
        df = pd.DataFrame(parsed)

        if df.empty:
            continue

        if time_col is None:
            time_col = df.columns[0]

        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    df[time_col] = pd.to_datetime(df[time_col], format="mixed")
    df = df.sort_values(time_col)
    df = df.drop_duplicates(subset=[time_col], keep="last")

    return df
