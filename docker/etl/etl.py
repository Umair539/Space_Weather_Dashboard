import logging

from src.extract.extract import extract_live_data, extract_saved_data
from src.load.load import load_raw_data, load_transformed_data
from src.transform.transform import transform_data

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        logger.info("Starting ETL pipeline")

        logger.info("Beginning live data extraction phase...")
        live_data = extract_live_data()
        logger.info("Live data extraction complete.")

        logger.info("Beginning raw data load phase...")
        load_raw_data(live_data)
        logger.info("Raw data load complete.")

        logger.info("Beginning saved data extraction phase...")
        saved_data = extract_saved_data(filter_raw=True)
        logger.info("Saved data extraction complete.")

        logger.info("Beginning transformation phase...")
        transformed_data = transform_data(saved_data)
        logger.info("Transformation complete.")

        logger.info("Beginning transformed data load phase...")
        load_transformed_data(transformed_data)
        logger.info("Transformed data load complete.")

        logger.info("ETL pipeline successful.")

    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        raise
