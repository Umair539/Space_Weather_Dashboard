import pandas as pd
from src.transform.process_solar_wind import cast_to_float
from src.transform.process_solar_wind import handle_missing_data
from src.transform.process_solar_wind import set_index_name


def process_smoothed_ssn(smoothed_ssn):
    smoothed_ssn = filter_smoothed_ssn(smoothed_ssn)
    smoothed_ssn = set_time_index(smoothed_ssn)
    smoothed_ssn = cast_to_float(smoothed_ssn)
    smoothed_ssn = handle_missing_data(smoothed_ssn)
    smoothed_ssn = set_index_name(smoothed_ssn)

    return smoothed_ssn


def filter_smoothed_ssn(smoothed_ssn):
    smoothed_ssn = smoothed_ssn[["time-tag", "predicted_ssn"]]
    return smoothed_ssn


def set_time_index(df):
    time_index_series = pd.to_datetime(df["time-tag"])
    df = df.set_index(time_index_series)
    df = df.drop(columns=["time-tag"])
    return df
