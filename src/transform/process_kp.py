from src.transform.process_rtsw import (
    set_time_index,
    cast_to_float,
    handle_missing_data,
    set_index_name,
    filter_columns,
)

KP_DATA_COLS = ["Kp"]


def process_kp(kp):
    kp = filter_columns(kp, KP_DATA_COLS)
    kp = set_time_index(kp)
    kp = cast_to_float(kp)
    kp = handle_missing_data(kp)
    kp = set_index_name(kp)
    return kp
