from src.transform.process_rtsw import (
    cast_to_float,
    handle_missing_data,
    set_index_name,
    set_time_index,
    filter_columns,
)

SMOOTHED_SSN_DATA_COLS = ["predicted_ssn"]


def process_smoothed_ssn(smoothed_ssn):
    smoothed_ssn = filter_columns(
        smoothed_ssn, SMOOTHED_SSN_DATA_COLS, time_col="time-tag"
    )
    smoothed_ssn = set_time_index(smoothed_ssn, "time-tag")
    smoothed_ssn = cast_to_float(smoothed_ssn)
    smoothed_ssn = handle_missing_data(smoothed_ssn)
    smoothed_ssn = set_index_name(smoothed_ssn)
    return smoothed_ssn
