import logging
from src.utils.parser import detect_format
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__, "extract_data.log", level=logging.DEBUG)


class SchemaError(Exception):
    """Raised when a NOAA payload is missing required columns for downstream transform."""


REQUIRED_COLUMNS = {
    "mag": {"time_tag", "active", "bz_gsm", "bx_gsm", "by_gsm", "bt"},
    "plasma": {
        "time_tag",
        "active",
        "proton_speed",
        "proton_temperature",
        "proton_density",
    },
    "dst": {"time_tag", "dst"},
    "kp": {"time_tag", "Kp"},
    "ssn": {"Obsdate", "swpc_ssn"},
    "smoothed_ssn": {"time-tag", "predicted_ssn"},
}


def validate_schema(name, data):
    if not data:
        raise SchemaError(f"{name}: empty data")

    fmt = detect_format(data)
    if fmt == "list_of_lists":
        columns = set(data[0])
    elif fmt == "list_of_dicts":
        columns = set(data[0].keys())
    else:
        raise SchemaError(f"{name}: unknown data structure")

    logger.info(f"{name} columns: {columns}")

    missing = REQUIRED_COLUMNS[name] - columns
    if missing:
        raise SchemaError(
            f"{name}: schema drift, missing {missing}, received {columns}"
        )
