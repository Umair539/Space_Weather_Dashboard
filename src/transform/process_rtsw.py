import pandas as pd
import logging
from src.transform.process_old_solar_wind import process_old_solar_wind
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__, "transform_data.log", level=logging.DEBUG)

MAG_DATA_COLS = ["bz_gsm", "bx_gsm", "by_gsm", "bt"]
PLASMA_DATA_COLS = ["proton_speed", "proton_temperature", "proton_density"]


def process_rtsw(mag, plasma, old_mag, old_plasma):

    logger.info(f"Input mag shape: {mag.shape}, plasma shape: {plasma.shape}")

    logger.info("Filtering columns...")
    mag = filter_columns(mag, MAG_DATA_COLS, extra_cols=["active"])
    plasma = filter_columns(plasma, PLASMA_DATA_COLS, extra_cols=["active"])

    logger.info("Filtering source...")
    mag = filter_source(mag, MAG_DATA_COLS)
    plasma = filter_source(plasma, PLASMA_DATA_COLS)

    logger.info("Dropping active column, formatting names, deduplicating...")
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

    logger.info("Setting time index...")
    mag = set_time_index(mag)
    plasma = set_time_index(plasma)

    if (
        old_mag is not None
        and not old_mag.empty
        and old_plasma is not None
        and not old_plasma.empty
    ):
        logger.info("Combining with old solar wind data...")
        old_mag, old_plasma = process_old_solar_wind(old_mag, old_plasma)
        mag = combine_dataframes(old_mag, mag)
        plasma = combine_dataframes(old_plasma, plasma)
        del old_mag, old_plasma

    logger.info("Matching time index...")
    mag, plasma = match_time_index(mag, plasma)
    logger.info(f"Matched time index shape: {mag.shape}")

    logger.info("Joining mag and plasma...")
    solar = join_mag_plasma(mag, plasma)
    del mag, plasma

    logger.info("Casting to float...")
    solar = cast_to_float(solar)

    logger.info("Filtering invalid data...")
    solar = filter_invalid_data(solar)

    logger.info("Filtering outliers...")
    solar = filter_outliers(solar)

    logger.info("Handling missing data...")
    solar = handle_missing_data(solar)

    solar = add_pressure_column(solar)
    solar = round_values(solar)
    solar = set_index_name(solar)

    logger.info(f"Solar wind processing complete. Output shape: {solar.shape}")
    return solar


def filter_columns(df, data_cols, extra_cols=None, time_col="time_tag"):
    if extra_cols is None:
        extra_cols = []
    return df[[time_col] + extra_cols + data_cols]


def filter_source(df, data_cols):
    df = df.sort_values(["time_tag", "active"], ascending=[True, False])

    # Split into active and inactive rows, indexed by timestamp
    active = df[df["active"]].set_index("time_tag")
    inactive = df[~df["active"]].set_index("time_tag")

    # Find timestamps where active row is entirely NaN
    active_all_nan = active[data_cols].isna().all(axis=1)
    fallback_timestamps = active_all_nan.index[active_all_nan]

    # Find inactive rows where all data columns are valid
    inactive_all_valid = inactive[data_cols].notna().all(axis=1)
    valid_inactive_timestamps = inactive_all_valid.index[inactive_all_valid]

    # Only replace where active is bad AND inactive is fully valid
    replaceable = fallback_timestamps.intersection(valid_inactive_timestamps)

    # Start with active rows, replace bad ones with valid inactive
    result = active.copy()
    result.loc[replaceable] = inactive.loc[replaceable]

    # Add timestamps that only exist in inactive (no active row at all)
    inactive_only = inactive.index.difference(active.index)
    if len(inactive_only) > 0:
        result = pd.concat([result, inactive.loc[inactive_only]])

    return result.reset_index()


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
    del time_index_series
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
    result = df.where(~(roc > roc.quantile(quantile)))
    del roc
    return result


def handle_missing_data(df):
    df = df.interpolate(method="linear", axis=0)
    df = df.ffill()
    df = df.bfill()
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
