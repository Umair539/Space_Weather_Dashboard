from src.extract.fetch_json import fetch_json
from src.extract.fetch_saved import fetch_saved
from src.utils.validator import SchemaError
from src.utils.logging_utils import setup_logger

logger = setup_logger("extract_data", "extract_data.log")

BASE_URL = "https://services.swpc.noaa.gov/"

MAG_URL = BASE_URL + "json/rtsw/rtsw_mag_1m.json"
PLASMA_URL = BASE_URL + "json/rtsw/rtsw_wind_1m.json"
DST_URL = BASE_URL + "products/kyoto-dst.json"
KP_URL = BASE_URL + "products/noaa-planetary-k-index.json"
SSN_URL = BASE_URL + "json/solar-cycle/swpc_observed_ssn.json"
SMOOTHED_SSN_URL = BASE_URL + "json/solar-cycle/predicted-solar-cycle.json"

DATA_SOURCES = {
    "mag": {"url": MAG_URL, "folder": "mag"},
    "plasma": {"url": PLASMA_URL, "folder": "plasma"},
    "dst": {"url": DST_URL, "folder": "dst"},
    "kp": {"url": KP_URL, "folder": "kp"},
    "ssn": {"url": SSN_URL, "folder": "ssn"},
    "smoothed_ssn": {"url": SMOOTHED_SSN_URL, "folder": "smoothed_ssn"},
    "old_mag": {"url": None, "folder": "old_mag"},
    "old_plasma": {"url": None, "folder": "old_plasma"},
}


def extract_live_data():
    logger.info("Starting live data extraction...")
    results = {}

    for name, source in DATA_SOURCES.items():
        if source["url"] is None:
            continue
        try:
            results[name] = fetch_json(source["url"], name)
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

    for name, source in DATA_SOURCES.items():
        try:
            results[name] = fetch_saved(source["folder"], filter_raw=filter_raw)
        except Exception as e:
            logger.error(f"Failed to fetch saved {name}: {e}")
            results[name] = None

    logger.info("Saved data extraction complete.")
    return results
