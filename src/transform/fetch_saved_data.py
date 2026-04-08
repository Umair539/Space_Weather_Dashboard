import os
import pandas as pd
import json
from src.utils.parser import parse_data


def fetch_saved_data(folder_path):
    dfs = []
    time_col = None  # will detect once

    for fname in ["lists.json", "dicts.json"]:
        path = os.path.join(folder_path, fname)

        if os.path.exists(path):
            with open(path, "r") as f:
                raw = json.load(f)

            if not raw:
                continue

            parsed = parse_data(raw)
            df = pd.DataFrame(parsed)

            if df.empty:
                continue

            # detect time column once
            if time_col is None:
                time_col = df.columns[0]

            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    # normalise time using original column name
    # handle different formats for time column using 'mixed'
    df[time_col] = pd.to_datetime(df[time_col], format="mixed")

    df = df.sort_values(time_col)
    df = df.drop_duplicates(subset=[time_col], keep="last")

    return df
