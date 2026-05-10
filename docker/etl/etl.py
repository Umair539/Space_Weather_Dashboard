import logging

from src.extract.extract import extract_data
from src.transform.transform import transform_data
from src.load.load import load_raw_data, load_transformed_data

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        logger.info("Starting ETL pipeline")

        logger.info("Beginning data extraction phase")
        extracted_data = extract_data()
        logger.info("Data extraction phase completed")

        logger.info("Beginning data load phase on raw data")
        updated_data = load_raw_data(extracted_data)
        logger.info("Completed data load phase on raw data")

        logger.info("Beginning data transformation phase")
        transformed_data = transform_data(updated_data)
        logger.info("Data transformation phase completed")

        logger.info("Beginning data load phase on transformed data")
        load_transformed_data(transformed_data)
        logger.info("Completed data load phase on transformed data")

        logger.info("ETL pipeline successful")

    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        raise
