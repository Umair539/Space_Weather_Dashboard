from src.extract.fetch_json import put_fetch_metric
from src.extract.fetch_saved import fetch_saved
from src.extract.fetch_s3 import fetch_s3_json
from src.extract.fetch_kp import fetch_kp
from src.extract.fetch_dst import fetch_dst
from src.utils.validator import SchemaError, validate_schema
from src.utils.logging_utils import setup_logger

logger = setup_logger("extract_data", "extract_data.log")

# services.swpc.noaa.gov now sits behind an AWS WAF challenge that blocks
# non-browser clients, so live data comes from alternative official sources.
MAG_S3_KEY = "json/rtsw/rtsw_mag_1m.json"
PLASMA_S3_KEY = "json/rtsw/rtsw_wind_1m.json"
SSN_S3_KEY = "json/solar-cycle/sunspots.json"
SMOOTHED_SSN_S3_KEY = "json/solar-cycle/sunspots-smoothed.json"


def _fetch_mag():
    return fetch_s3_json(MAG_S3_KEY)


def _fetch_plasma():
    return fetch_s3_json(PLASMA_S3_KEY)


def _fetch_ssn():
    return [
        {"Obsdate": row["time-tag"], "swpc_ssn": row["ssn"]}
        for row in fetch_s3_json(SSN_S3_KEY)
    ]


def _fetch_smoothed_ssn():
    return [
        {"time-tag": row["time-tag"], "predicted_ssn": row["smoothed_ssn"]}
        for row in fetch_s3_json(SMOOTHED_SSN_S3_KEY)
    ]


LIVE_FETCHERS = {
    "mag": _fetch_mag,
    "plasma": _fetch_plasma,
    "dst": fetch_dst,
    "kp": fetch_kp,
    "ssn": _fetch_ssn,
    "smoothed_ssn": _fetch_smoothed_ssn,
}

DATA_FOLDERS = {
    "mag": "mag",
    "plasma": "plasma",
    "dst": "dst",
    "kp": "kp",
    "ssn": "ssn",
    "smoothed_ssn": "smoothed_ssn",
    "old_mag": "old_mag",
    "old_plasma": "old_plasma",
}


def extract_live_data():
    logger.info("Starting live data extraction...")
    results = {}

    for name, fetcher in LIVE_FETCHERS.items():
        try:
            data = fetcher()
            validate_schema(name, data)
            results[name] = data
            logger.info(f"Successfully retrieved data for {name}")
            put_fetch_metric(name)
        except SchemaError as e:
            logger.error(f"Schema drift in {name}: {e}")
            results[name] = None
        except Exception as e:
            logger.warning(f"Failed to fetch {name}: {e}")
            results[name] = None

    logger.info("Live data extraction complete.")
    return results


def extract_saved_data(filter_raw=True):
    logger.info(f"Starting saved data extraction [filter_raw={filter_raw}]...")
    results = {}

    for name, folder in DATA_FOLDERS.items():
        try:
            results[name] = fetch_saved(folder, filter_raw=filter_raw)
        except Exception as e:
            logger.error(f"Failed to fetch saved {name}: {e}")
            results[name] = None

    logger.info("Saved data extraction complete.")
    return results
