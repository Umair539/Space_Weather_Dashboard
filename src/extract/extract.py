from concurrent.futures import ThreadPoolExecutor

from src.utils.fetch_utils import put_fetch_metric
from src.extract.fetch_saved import fetch_saved
from src.extract.fetch_rtsw import fetch_mag, fetch_plasma
from src.extract.fetch_kp import fetch_kp
from src.extract.fetch_dst import fetch_dst
from src.extract.fetch_ssn import fetch_ssn
from src.extract.fetch_smoothed_ssn import fetch_smoothed_ssn
from src.utils.logging_utils import setup_logger

logger = setup_logger("extract_data", "extract_data.log")

# Each fetcher below tries NOAA (services.swpc.noaa.gov) first, then falls
# back to an alternative official source if NOAA's AWS WAF blocks it - see
# fetch_with_fallback inside each fetch_*.py module for the retry/fallback
# logic and the CloudWatch failure metric it emits if both sources fail.

LIVE_FETCHERS = {
    "mag": fetch_mag,
    "plasma": fetch_plasma,
    "dst": fetch_dst,
    "kp": fetch_kp,
    "ssn": fetch_ssn,
    "smoothed_ssn": fetch_smoothed_ssn,
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
            results[name] = fetcher()
            logger.info(f"Successfully retrieved data for {name}")
            put_fetch_metric(name)
        except Exception as e:
            logger.error(f"Failed to fetch {name} from primary and fallback: {e}")
            results[name] = None

    logger.info("Live data extraction complete.")
    return results


def _fetch_saved_one(name, folder, filter_raw):
    try:
        return name, fetch_saved(folder, filter_raw=filter_raw)
    except Exception as e:
        logger.error(f"Failed to fetch saved {name}: {e}")
        return name, None


def extract_saved_data(filter_raw=True):
    logger.info(f"Starting saved data extraction [filter_raw={filter_raw}]...")

    # Each source reads its own storage keys with no shared state - same
    # independent-I/O shape as the raw load phase, so fetch them concurrently
    # instead of sequentially.
    with ThreadPoolExecutor(max_workers=len(DATA_FOLDERS)) as executor:
        futures = [
            executor.submit(_fetch_saved_one, name, folder, filter_raw)
            for name, folder in DATA_FOLDERS.items()
        ]
        results = dict(future.result() for future in futures)

    logger.info("Saved data extraction complete.")
    return results
