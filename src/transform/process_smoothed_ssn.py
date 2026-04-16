from src.transform.process_rtsw import cast_to_float
from src.transform.process_rtsw import handle_missing_data
from src.transform.process_rtsw import set_index_name
from src.transform.process_rtsw import set_time_index


def process_smoothed_ssn(smoothed_ssn):
    smoothed_ssn = filter_smoothed_ssn(smoothed_ssn)
    smoothed_ssn = set_time_index(smoothed_ssn, "time-tag")
    smoothed_ssn = cast_to_float(smoothed_ssn)
    smoothed_ssn = handle_missing_data(smoothed_ssn)
    smoothed_ssn = set_index_name(smoothed_ssn)

    return smoothed_ssn


def filter_smoothed_ssn(smoothed_ssn):
    smoothed_ssn = smoothed_ssn[["time-tag", "predicted_ssn"]]
    return smoothed_ssn
