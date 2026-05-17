from src.transform.process_rtsw import (
    cast_to_float,
    handle_missing_data,
    set_index_name,
    set_time_index,
    filter_columns,
)

SSN_DATA_COLS = ["ssn"]
TWELVE_YEARS_IN_DAYS = int(12 * 365.25)


def process_ssn(ssn):
    ssn = filter_columns(ssn, SSN_DATA_COLS, time_col="Obsdate")
    ssn = set_time_index(ssn, "Obsdate")
    ssn = cast_to_float(ssn)
    ssn = handle_missing_data(ssn)
    ssn = set_index_name(ssn)
    ssn = filter_ssn(ssn)
    return ssn


def filter_ssn(ssn):
    return ssn.iloc[-TWELVE_YEARS_IN_DAYS:]
