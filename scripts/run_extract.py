from src.extract.extract import extract_data
from src.load.load import load_raw_data
from src.utils.logging_utils import setup_logger
import time


def run_extract(loop=False):
    # Setup ETL pipeline logger
    logger = setup_logger("extract", "extract.log")
    while True:
        try:
            logger.info("Starting ETL pipeline")

            # Extraction phase
            logger.info("Beginning data extraction phase")
            extracted_data = extract_data()
            logger.info("Data extraction phase completed")

            # Load raw data
            logger.info("Beginning data load phase on raw data")
            load_raw_data(extracted_data)
            logger.info("Completed data load phase on raw data")

            logger.info("Extract successful")

        except Exception as e:
            logger.error(f"Extract failed: {e}")

        if not loop:
            break

        logger.info("Sleeping for 60 seconds")
        time.sleep(60)
