import pandas as pd
from src.transform.process_old_solar_wind import process_old_solar_wind


def process_rtsw(mag, plasma, old_mag, old_plasma):

    old_mag, old_plasma = process_old_solar_wind(old_mag, old_plasma)

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

    mag = combine_dataframes(old_mag, mag)
    plasma = combine_dataframes(old_plasma, plasma)

    mag, plasma = match_time_index(mag, plasma)

    solar = join_mag_plasma(mag, plasma)

    solar = cast_to_float(solar)

    solar = filter_invalid_data(solar)
    solar = filter_outliers(solar)
    solar = handle_missing_data(solar)

    solar = add_pressure_column(solar)
    solar = round_values(solar)
    solar = set_index_name(solar)

    return solar


def filter_columns(df, data_cols):
    return df[["time_tag", "active"] + data_cols]


def filter_source(df, data_cols):
    df = df.sort_values(["time_tag", "active"], ascending=[True, False])

    df = (
        df.groupby("time_tag", sort=False)
        .apply(pick_row, data_cols=data_cols, include_groups=False)
        .reset_index()
    )

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


def combine_dataframes(old_df, new_df):
    new_only = new_df[~new_df.index.isin(old_df.index)]
    return pd.concat([old_df, new_only]).sort_index()


def match_time_index(mag, plasma):
    start_time = min(mag.index.min(), plasma.index.min())
    end_time = max(mag.index.max(), plasma.index.max())

    full_range = pd.date_range(start=start_time, end=end_time, freq="min")

    mag = mag.reindex(full_range)
    plasma = plasma.reindex(full_range)
    return mag, plasma


def join_mag_plasma(mag, plasma):
    solar = plasma.join(mag, how="outer")
    return solar


def cast_to_float(df):
    df = df.astype("float64")
    return df


def filter_invalid_data(solar):
    cols = ["density", "speed", "temperature"]
    solar[cols] = solar[cols].mask(solar[cols] <= 0)
    return solar


def filter_outliers(df, quantile=0.97):
    roc = df.diff().abs()
    mask = roc > roc.quantile(quantile)
    return df.where(~mask)


def handle_missing_data(df):
    df = df.interpolate(method="linear", axis=0).ffill().bfill()
    return df


def add_pressure_column(solar):
    proton_mass = 1.6726e-27
    solar["pressure"] = (
        proton_mass * solar["density"] * 1e6 * (solar["speed"] ** 2) * 1e6 * 1e9
    )
    return solar


def round_values(df):
    return df.round(2)


def set_index_name(df):
    df.index.name = "time"
    return df
