import pandas as pd


def process_old_solar_wind(mag, plasma):

    mag = filter_columns(mag, ["bz_gsm", "bx_gsm", "by_gsm", "bt"])
    mag = format_column_names(
        mag, columns={"bz_gsm": "bz", "bx_gsm": "bx", "by_gsm": "by"}
    )

    mag = drop_duplicates(mag)
    plasma = drop_duplicates(plasma)

    mag = set_time_index(mag)
    plasma = set_time_index(plasma)

    return mag, plasma


def filter_columns(df, data_cols):
    return df[["time_tag"] + data_cols]


def format_column_names(df, columns):
    df = df.rename(columns=columns)
    return df


def drop_duplicates(df):
    return df.drop_duplicates()


def set_time_index(df, time_col="time_tag"):
    time_index_series = pd.to_datetime(df[time_col])
    df = df.set_index(time_index_series)
    df = df.drop(columns=[time_col])
    return df
