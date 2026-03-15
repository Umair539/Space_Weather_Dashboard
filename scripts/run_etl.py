from src.extract.extract import extract_data
from src.transform.transform import transform_data
from src.load.load import load_raw_data
from src.load.load import load_transformed_data
from src.utils.logging_utils import setup_logger
import time


def run_etl_pipeline():
    # Setup ETL pipeline logger
    logger = setup_logger("etl_pipeline", "etl_pipeline.log")
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

            # Transformation phase
            logger.info("Beginning data transformation phase")
            transformed_data = transform_data()
            logger.info("Data transformation phase completed")

            # Load transformed data
            logger.info("Beginning data load phase on transformed data")
            load_transformed_data(transformed_data)
            logger.info("Completed data load phase on transformed data")

            logger.info("ETL pipeline successful")

        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}")

        logger.info("Sleeping for 60 seconds")
        time.sleep(60)
