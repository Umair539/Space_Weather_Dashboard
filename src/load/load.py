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


def load_raw_data(extracted_data):
    logger.info("Loading raw data to cloud...")

    for name, loader in LOADERS.items():
        data = extracted_data.get(name)
        if data is None:
            logger.warning(f"No data for {name}, skipping.")
            continue
        try:
            loader(name, data)
        except Exception as e:
            logger.error(f"Failed to load {name}: {e}")

    logger.info("Raw data loading complete.")


def load_transformed_data(transformed_data, upsert_hours=24 * 7):
    try:
        logger.info("Saving transformed data to Supabase SQL database...")
        load_data_into_db(transformed_data, upsert_hours=upsert_hours)
        logger.info("Supabase SQL database updated successfully.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
        raise
