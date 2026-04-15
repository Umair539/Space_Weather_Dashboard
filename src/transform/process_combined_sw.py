import pandas as pd
from src.transform.process_solar_wind import process_solar_wind
from src.transform.process_rtsw import process_rtsw


def process_combined_sw(old_mag, old_plasma, mag, plasma):
    old_mag, old_plasma = process_solar_wind(old_mag, old_plasma)
    mag, plasma = process_rtsw(mag, plasma)

    mag = combine_dataframes(old_mag, mag)
    plasma = combine_dataframes(old_plasma, plasma)

    mag, plasma = match_time_index(mag, plasma)

    solar = join_mag_plasma(mag, plasma)

    solar = cast_to_float(solar)
    solar = filter_invalid_data(solar)
    solar = handle_missing_data(solar)

    solar = add_pressure_column(solar)
    solar = round_values(solar)
    solar = set_index_name(solar)

    return solar


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
