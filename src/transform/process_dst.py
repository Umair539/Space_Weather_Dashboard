from src.transform.process_solar_wind import set_time_index
from src.transform.process_solar_wind import cast_to_float
from src.transform.process_solar_wind import interpolate_missing_data

def process_dst(dst):
    dst = set_time_index(dst)
    dst = cast_to_float(dst)
    dst = interpolate_missing_data(dst)
    return dst