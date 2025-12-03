from src.extract.extract import extract_data
from src.transform.transform import transform_data
from src.load.load import load_raw_data
from src.load.load import load_transformed_data
from src.utils.logging_utils import setup_logger
import time


def main():
    # Setup ETL pipeline logger
    logger = setup_logger("etl_pipeline", "etl_pipeline.log")
    while True:
        print("Attempting ETL")
        try:
            logger.info("Starting ETL pipeline")

            # Extraction phase
            logger.info("Beginning data extraction phase")
            extracted_data = extract_data()
            logger.info("Data extraction phase completed")

            # Load phase on raw data
            logger.info("Beginning data load phase on raw data")
            load_raw_data(extracted_data)
            logger.info("Completed data load phase on raw data")

            # Transformation phase
            logger.info("Beginning data transformation phase")
            transformed_data = transform_data(extracted_data)
            logger.info("Data transformation phase completed")

            # Load phase on transformed data
            logger.info("Beginning data load phase on transformed data")
            load_transformed_data(transformed_data)
            logger.info("Completed data load phase on transformed data")

            del extracted_data
            del transformed_data

            print("ETL successful")

        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}")
            print("ETL unsuccessful")

        print("Sleeping for 60 seconds")
        time.sleep(60)


if __name__ == "__main__":
    main()
