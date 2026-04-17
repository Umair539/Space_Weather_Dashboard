from src.utils.logging_utils import setup_logger
from src.load.load_raw_json import load_raw_json
from src.load.load_data_into_db import load_data_into_db
from src.load.load_raw_rtsw import load_raw_rtsw

logger = setup_logger("load_data", "load_data.log")


def load_raw_data(extracted_data):
    old_mag, old_plasma, mag, plasma, dst, kp, ssn, smoothed_ssn = extracted_data
    logger.info("Loading raw data...")

    for folder_path, loader, data in [
        ("mag", load_raw_json, old_mag),
        ("plasma", load_raw_json, old_plasma),
        ("mag", load_raw_rtsw, mag),
        ("plasma", load_raw_rtsw, plasma),
        ("dst", load_raw_json, dst),
        ("kp", load_raw_json, kp),
        ("ssn", load_raw_json, ssn),
        ("smoothed_ssn", load_raw_json, smoothed_ssn),
    ]:
        try:
            loader(folder_path, data)
        except Exception as e:
            logger.error(f"Failed to load {folder_path}: {e}")

    logger.info("Raw data loading complete.")


def load_transformed_data(transformed_data):
    try:
        logger.info("Saving transformed data to Neon SQL database...")
        load_data_into_db(transformed_data)
        logger.info("Neon SQL database updated successfully.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
        raise
