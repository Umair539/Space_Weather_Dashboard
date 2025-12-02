from src.transform.process_solar_wind import set_time_index
from src.transform.process_solar_wind import cast_to_float
from src.transform.process_solar_wind import interpolate_missing_data

def process_kp(kp):
    kp = filter_columns(kp)
    kp = set_time_index(kp)
    kp = cast_to_float(kp)
    kp = interpolate_missing_data(kp)
    return kp

def filter_columns(kp):
    kp = kp[['time_tag', 'Kp']]
    return kp