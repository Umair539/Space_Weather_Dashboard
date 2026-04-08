from src.transform.process_solar_wind import cast_to_float
from src.transform.process_solar_wind import handle_missing_data
from src.transform.process_solar_wind import set_index_name
from src.transform.process_solar_wind import set_time_index


def process_ssn(ssn):
    ssn = set_time_index(ssn, "Obsdate")
    ssn = cast_to_float(ssn)
    ssn = handle_missing_data(ssn)
    ssn = set_index_name(ssn)
    ssn = filter_ssn(ssn)

    return ssn


def filter_ssn(ssn):
    return ssn.iloc[-4383:]
