from src.utils.logging_utils import setup_logger
from src.load.load_raw_json import load_raw_json
from src.load.load_data_into_db import load_data_into_db

logger = setup_logger("load_data", "load_data.log")


def load_raw_data(extracted_data):
    try:
        mag, plasma, dst, kp, ssn, smoothed_ssn = extracted_data

        logger.info("Loading raw data...")

        load_raw_json("mag", mag)
        load_raw_json("plasma", plasma)
        load_raw_json("dst", dst)
        load_raw_json("kp", kp)
        load_raw_json("ssn", ssn)
        load_raw_json("smoothed_ssn", smoothed_ssn)

        logger.info("Loaded raw data.")

    except Exception as e:
        logger.error(f"Failed to load raw data: {str(e)}")


def load_transformed_data(transformed_data):
    try:
        logger.info("Saving transformed data to Neon SQL database...")
        load_data_into_db(transformed_data)
        logger.info("Neon SQL database updated successfully.")

    except Exception as e:
        logger.error(f"Failed to load transformed data: {str(e)}")
        raise
