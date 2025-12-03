from src.transform.process_solar_wind import set_time_index
from src.transform.process_solar_wind import cast_to_float
from src.transform.process_solar_wind import handle_missing_data
from src.transform.process_solar_wind import set_index_name


def process_dst(dst):
    dst = set_time_index(dst)
    dst = cast_to_float(dst)
    dst = handle_missing_data(dst)
    dst = set_index_name(dst)
    return dst
