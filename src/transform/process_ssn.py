import pandas as pd
from src.transform.process_solar_wind import cast_to_float
from src.transform.process_solar_wind import handle_missing_data
from src.transform.process_solar_wind import set_index_name


def process_ssn(ssn):
    ssn = set_time_index(ssn)
    ssn = cast_to_float(ssn)
    ssn = handle_missing_data(ssn)
    ssn = set_index_name(ssn)
    ssn = filter_ssn(ssn)

    return ssn


def filter_ssn(ssn):
    return ssn.iloc[-366:]


def set_time_index(df):
    time_index_series = pd.to_datetime(df["Obsdate"])
    df = df.set_index(time_index_series)
    df = df.drop(columns=["Obsdate"])
    return df
