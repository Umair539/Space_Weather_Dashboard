from concurrent.futures import ThreadPoolExecutor

from src.utils.logging_utils import setup_logger
from src.load.load_raw_json import load_raw_json
from src.load.load_raw_rtsw import load_raw_rtsw
from src.load.load_data_into_db import load_data_into_db

logger = setup_logger("load_data", "load_data.log")

LOADERS = {
    "mag": load_raw_rtsw,
    "plasma": load_raw_rtsw,
    "dst": load_raw_json,
    "kp": load_raw_json,
    "ssn": load_raw_json,
    "smoothed_ssn": load_raw_json,
}


def _load_one(name, loader, data):
    try:
        logger.info(f"Loading {name}...")
        loader(name, data)
        logger.info(f"Loaded {name}.")
    except Exception as e:
        logger.error(f"Failed to load {name}: {e}")


def load_raw_data(extracted_data):
    logger.info("Loading raw data to cloud...")

    # Each source writes to its own S3/R2 keys with no shared state, so these
    # are independent I/O-bound calls - running them on a thread pool instead
    # of sequentially collapses total wall time to roughly the slowest single
    # loader instead of the sum of all of them. boto3 clients are thread-safe.
    with ThreadPoolExecutor(max_workers=len(LOADERS)) as executor:
        for name, loader in LOADERS.items():
            data = extracted_data.get(name)
            if data is None:
                logger.warning(f"No data for {name}, skipping.")
                continue
            executor.submit(_load_one, name, loader, data)

    logger.info("Raw data loading complete.")


def load_transformed_data(transformed_data, upsert_hours=24 * 7):
    try:
        logger.info("Saving transformed data to Supabase SQL database...")
        load_data_into_db(transformed_data, upsert_hours=upsert_hours)
        logger.info("Supabase SQL database updated successfully.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
        raise
