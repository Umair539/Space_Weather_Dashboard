from src.transform.process_rtsw import (
    set_time_index,
    cast_to_float,
    handle_missing_data,
    set_index_name,
    filter_columns,
)

DST_DATA_COLS = ["dst"]


def process_dst(dst):
    dst = filter_columns(dst, DST_DATA_COLS)
    dst = set_time_index(dst)
    dst = cast_to_float(dst)
    dst = handle_missing_data(dst)
    dst = set_index_name(dst)
    return dst
