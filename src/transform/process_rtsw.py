import pandas as pd


def process_rtsw(mag, plasma):

    mag = filter_columns(mag, ["bz_gsm", "bx_gsm", "by_gsm", "bt"])
    plasma = filter_columns(
        plasma, ["proton_speed", "proton_temperature", "proton_density"]
    )

    mag = filter_source(mag, ["bz_gsm", "bx_gsm", "by_gsm", "bt"])
    plasma = filter_source(
        plasma, ["proton_speed", "proton_temperature", "proton_density"]
    )

    mag = drop_active_column(mag)
    plasma = drop_active_column(plasma)

    mag = format_column_names(
        mag, columns={"bz_gsm": "bz", "bx_gsm": "bx", "by_gsm": "by"}
    )
    plasma = format_column_names(
        plasma,
        columns={
            "proton_speed": "speed",
            "proton_temperature": "temperature",
            "proton_density": "density",
        },
    )

    mag = drop_duplicates(mag)
    plasma = drop_duplicates(plasma)

    mag = set_time_index(mag)
    plasma = set_time_index(plasma)

    return mag, plasma


def filter_columns(df, data_cols):
    return df[["time_tag", "active"] + data_cols]


def filter_source(df, data_cols):
    df = df.sort_values(["time_tag", "active"], ascending=[True, False])

    df = df.groupby("time_tag", sort=False).apply(
        pick_row, data_cols=data_cols, include_groups=False
    ).reset_index()

    return df


def pick_row(g, data_cols):
    active_row = g.iloc[0]
    inactive_row = g.iloc[-1] if len(g) > 1 else None

    active_all_nan = active_row[data_cols].isna().all()

    if (
        active_all_nan
        and inactive_row is not None
        and inactive_row[data_cols].notna().all()
    ):
        return inactive_row
    return active_row


def format_column_names(df, columns):
    df = df.rename(columns=columns)
    return df


def drop_active_column(df):
    return df.drop(columns=["active"])


def drop_duplicates(df):
    return df.drop_duplicates()


def set_time_index(df, time_col="time_tag"):
    time_index_series = pd.to_datetime(df[time_col])
    df = df.set_index(time_index_series)
    df = df.drop(columns=[time_col])
    return df
